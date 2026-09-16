"""Read-only Loyverse catalogue mirror.

GET only. This module never writes to the POS and never registers a webhook.
A person asks for each refresh, and since 16 September a once-a-day scheduled
read runs as well at the owner's explicit request. Every call is audited against
a real identity, and the account rate limit is bounded by a cooldown and a daily
cap. A schedule that only reads is still not permission to write.

Honesty rules that the rest of the app depends on:
  * A number that the source did not supply stays missing. It never becomes zero.
  * An item with `track_stock` false has no stock figure. Loyverse zeroes those
    inventory levels, so reporting the zero would invent a count.
  * A tracked variant with no inventory level for a store is unknown, not empty.
  * `optimal_stock` and `low_stock` default to null upstream: absent means the
    owner has not set a target, not that the target is zero.
  * Money and quantities are exact decimals parsed from the response bytes.
    Nothing here computes stock value, margin, or profit.
"""
import json
import os
import secrets
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import httpx
from fastapi import HTTPException

from .db import audit, connect, data_dir, now, password_hash
from . import performance

BASE = 'https://api.loyverse.com/v1.0'
PAGE_SIZE = 250
MAX_PAGES = 40
SCHEMA_VERSION = 2
WORKSPACE_STORES = ('sausage', 'health')
KEEP_PAYLOADS = 3
KEEP_ROWS = 50
# Receipts are filtered on created_at but counted by receipt_date, so the fetch
# starts earlier than the window to pick up sales that were uploaded late.
LATE_UPLOAD_GRACE_DAYS = 4
# A reserved .invalid address that can never receive mail, holding a discarded
# password so the scheduled reader has an auditable identity but no way in.
SYSTEM_ACTOR_EMAIL = 'scheduled-sync@sausage-health.invalid'
LIMITATIONS = [
    'A read-only mirror of the Loyverse catalogue, captured when someone pressed refresh.',
    'Stock is the figure Loyverse held at capture time. It is not a physical count.',
    'Cost is the number recorded in Loyverse. Actual unit cost is still unverified.',
    'Items whose stock is not tracked, and stores with no inventory level, are reported as such and never as zero.',
    'Sales per week count receipts by their business date. A late upload can still change a recent week.',
    'Sales are counted units only. No margin, stock value or profit is derived here.',
]


def enabled():
    return os.environ.get('SH_LOYVERSE_ENABLED') == '1'


def token():
    """Environment first, then the documented private admin file. Never logged."""
    value = os.environ.get('SH_LOYVERSE_TOKEN', '').strip()
    if value:
        return value
    try:
        path = data_dir() / 'loyverse-access.json'
        stored = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError, RuntimeError):
        return ''
    found = stored.get('access_token') or stored.get('token') or '' if isinstance(stored, dict) else ''
    return found.strip() if isinstance(found, str) else ''


def configured():
    # The existence of a credential is not authority to replay it on a schedule.
    return enabled() and bool(token())


def store_map():
    """Loyverse store id -> workspace store. An unmapped store stays unattributed."""
    raw = os.environ.get('SH_LOYVERSE_STORE_MAP', '').strip()
    if not raw:
        return {}
    try:
        mapping = json.loads(raw)
    except ValueError:
        raise ValueError('SH_LOYVERSE_STORE_MAP is not valid JSON.')
    if not isinstance(mapping, dict) or not all(
            isinstance(key, str) and value in WORKSPACE_STORES for key, value in mapping.items()):
        raise ValueError('SH_LOYVERSE_STORE_MAP must map Loyverse store ids to "sausage" or "health".')
    return mapping


def number(value):
    """Exact source numbers only. Missing stays missing; float and bool are refused."""
    if value is None:
        return None
    if isinstance(value, (bool, float)):
        raise ValueError('Expected an exact source number, not float/bool')
    try:
        result = Decimal(value)
    except (InvalidOperation, TypeError):
        raise ValueError('Unreadable source number')
    if not result.is_finite():
        raise ValueError('Non-finite source number')
    return result


def text(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def digits(value):
    """Exact plain notation. `str` can emit 1E+3, which reads as nonsense in a table."""
    return None if value is None else format(value, 'f')


def get_pages(client, path, key, params=None):
    """Bounded cursor pagination. A partial chain raises instead of publishing a gap."""
    results, cursor, pages = [], None, 0
    while True:
        query = dict(params or {}, limit=PAGE_SIZE)
        if cursor:
            query['cursor'] = cursor
        response = client.get(BASE + path, params=query)
        if response.status_code == 429:
            raise HTTPException(429, 'Loyverse is rate limiting this account. Wait a few minutes before refreshing again.')
        if response.status_code in (401, 403):
            raise HTTPException(502, 'Loyverse refused the stored access credential. Ask the technical owner to check it.')
        response.raise_for_status()
        body = json.loads(response.content, parse_float=Decimal)
        batch = body.get(key) if isinstance(body, dict) else None
        if not isinstance(batch, list):
            raise ValueError('Unexpected Loyverse response shape for ' + key)
        results.extend(batch)
        pages += 1
        cursor = text(body.get('cursor'))
        if not cursor:
            return results, pages
        if pages >= MAX_PAGES:
            raise ValueError('This catalogue is larger than the bounded reader supports: ' + key)


def history_days():
    """How far back the dashboard reads. The account may simply hold less."""
    return bounded('SH_LOYVERSE_HISTORY_DAYS', '400', 1100)


def sales_days():
    """Whole weeks only, so a weekly average never divides by a ragged window."""
    requested = bounded('SH_LOYVERSE_SALES_DAYS', '28', 371)
    return max(7, (requested // 7) * 7)


def business_date(value):
    """Loyverse business dates are UTC instants; the calendar day is what reporting uses."""
    stamp = text(value)
    if not stamp:
        return None
    try:
        parsed = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError('Unreadable receipt date')
    if parsed.tzinfo is None:
        raise ValueError('Receipt date has no timezone')
    return parsed.astimezone(timezone.utc)


def aggregate_sales(receipts, start, end):
    """Net units per variant and store, bucketed into whole weeks by business date.

    A refund arrives as a positive magnitude, so the sign is applied exactly once
    here. Cancelled receipts and anything that is not a sale or refund are counted
    separately and never silently folded into a total.
    """
    weeks = (end - start).days // 7
    if weeks < 1:
        raise ValueError('A sales window needs at least one whole week')
    sold = defaultdict(lambda: {'units': Decimal(0), 'weekly': [Decimal(0)] * weeks})
    counted = cancelled = other = outside = 0
    refunds = 0
    for receipt in receipts:
        if text(receipt.get('cancelled_at')):
            cancelled += 1
            continue
        kind = text(receipt.get('receipt_type'))
        if kind not in ('SALE', 'REFUND'):
            other += 1
            continue
        moment = business_date(receipt.get('receipt_date'))
        if moment is None or not start <= moment < end:
            outside += 1
            continue
        index = min(weeks - 1, (moment - start).days // 7)
        sign = -1 if kind == 'REFUND' else 1
        refunds += kind == 'REFUND'
        counted += 1
        store_id = text(receipt.get('store_id'))
        for line in receipt.get('line_items') or []:
            variant_id = text(line.get('variant_id'))
            if not variant_id or not store_id:
                continue
            quantity = number(line.get('quantity'))
            if quantity is None:
                continue
            entry = sold[(variant_id, store_id)]
            entry['units'] += sign * quantity
            entry['weekly'][index] += sign * quantity
    return sold, {'window_days': (end - start).days, 'weeks': weeks,
                  'from': start.isoformat(), 'to': end.isoformat(),
                  'counted_receipts': counted, 'refund_receipts': refunds,
                  'cancelled_skipped': cancelled, 'other_types_skipped': other,
                  'outside_window_skipped': outside, 'basis': 'receipt_date'}


def sales_row(sold, variant_id, store_id, weeks):
    """A variant with no line in the window genuinely sold nothing we can see."""
    entry = sold.get((variant_id, store_id))
    units = entry['units'] if entry else Decimal(0)
    weekly = entry['weekly'] if entry else [Decimal(0)] * weeks
    average = (units / weeks).quantize(Decimal('0.01'))
    return {'sold_units': digits(units), 'sold_per_week': digits(average),
            'weekly_units': [digits(value) for value in weekly]}

def capture():
    """Read-only GETs against official endpoints. No writes, no redirects, no tools."""
    headers = {'Authorization': 'Bearer ' + token(), 'Accept': 'application/json'}
    requests_made = 0
    days = sales_days()
    end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=days)
    stamp = lambda moment: moment.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    with httpx.Client(timeout=60, follow_redirects=False, headers=headers) as client:
        merchant = client.get(BASE + '/merchant/')
        if merchant.status_code in (401, 403):
            raise HTTPException(502, 'Loyverse refused the stored access credential. Ask the technical owner to check it.')
        merchant.raise_for_status()
        requests_made += 1
        profile = json.loads(merchant.content, parse_float=Decimal)
        stores, pages = get_pages(client, '/stores', 'stores')
        requests_made += pages
        categories, pages = get_pages(client, '/categories', 'categories')
        requests_made += pages
        items, pages = get_pages(client, '/items', 'items')
        requests_made += pages
        inventory, pages = get_pages(client, '/inventory', 'inventory_levels')
        requests_made += pages
        # One fetch serves both: the weekly column slices the window out of it,
        # and the dashboard uses the whole history. Receipts are filtered on
        # created_at but counted by receipt_date, and late uploads happen here.
        receipts, pages = get_pages(client, '/receipts', 'receipts', {
            'created_at_min': stamp(end - timedelta(days=history_days())),
            'created_at_max': stamp(end)})
        requests_made += pages
    sold, sales = aggregate_sales(receipts, start, end)
    trading = performance.build(receipts, [store['id'] for store in stores if store.get('id')])
    currency = profile.get('currency') if isinstance(profile, dict) else None
    money = {'code': text(currency.get('code')) if isinstance(currency, dict) else None,
             'decimal_places': currency.get('decimal_places') if isinstance(currency, dict) else None}
    if not isinstance(money['decimal_places'], int) or isinstance(money['decimal_places'], bool):
        money['decimal_places'] = None
    return build(stores, categories, items, inventory, store_map(), money, sold, sales, trading), requests_made


def index_stores(stores, mapping):
    rows, seen = [], set()
    for store in stores:
        store_id = text(store.get('id'))
        if not store_id:
            raise ValueError('A Loyverse store has no id.')
        if store_id in seen:
            raise ValueError('Duplicate Loyverse store id.')
        seen.add(store_id)
        rows.append({'id': store_id, 'name': text(store.get('name')),
                     'workspace_store': mapping.get(store_id)})
    claimed = list(mapping.values())
    if len(claimed) != len(set(claimed)):
        raise ValueError('SH_LOYVERSE_STORE_MAP points two Loyverse stores at one workspace store.')
    return rows, sorted(set(mapping) - seen)


def index_inventory(inventory):
    levels = {}
    for level in inventory:
        key = (text(level.get('variant_id')), text(level.get('store_id')))
        if None in key:
            raise ValueError('An inventory level is missing its variant or store identity.')
        if key in levels:
            raise ValueError('Duplicate inventory level for one variant and store.')
        levels[key] = {'in_stock': number(level.get('in_stock')), 'updated_at': text(level.get('updated_at'))}
    return levels


def variant_store_row(entry, store, levels, variant_id, track_stock, components_only,
                      sold=None, weeks=None):
    """One variant in one store. Absent settings and absent stock stay absent."""
    row = {'store_id': store['id'], 'store_name': store['name'],
           'workspace_store': store['workspace_store'], 'settings_present': entry is not None,
           'available_for_sale': None, 'pricing_type': None, 'price': None,
           'optimal_stock': None, 'low_stock': None}
    if entry is not None:
        available = entry.get('available_for_sale')
        row['available_for_sale'] = available if isinstance(available, bool) else None
        row['pricing_type'] = text(entry.get('pricing_type'))
        row['price'] = digits(number(entry.get('price')))
        row['optimal_stock'] = digits(number(entry.get('optimal_stock')))
        row['low_stock'] = digits(number(entry.get('low_stock')))
    level = levels.get((variant_id, store['id']))
    if not track_stock:
        # Loyverse sets these levels to 0; reporting that zero would invent a count.
        row.update(stock_state='not_tracked', in_stock=None, stock_updated_at=None)
    elif components_only:
        row.update(stock_state='components_only', in_stock=None, stock_updated_at=None)
    elif level is None or level['in_stock'] is None:
        row.update(stock_state='unknown', in_stock=None, stock_updated_at=None)
    else:
        row.update(stock_state='tracked', in_stock=digits(level['in_stock']),
                   stock_updated_at=level['updated_at'])
    row['below_optimal'] = None
    row['low_stock_alert'] = False
    if row['stock_state'] == 'tracked':
        in_stock = Decimal(row['in_stock'])
        if row['optimal_stock'] is not None and in_stock < Decimal(row['optimal_stock']):
            row['below_optimal'] = digits(Decimal(row['optimal_stock']) - in_stock)
        if row['low_stock'] is not None and in_stock <= Decimal(row['low_stock']):
            row['low_stock_alert'] = True
    # Without a sales window the figures are absent, not zero: an old snapshot
    # carries no receipts, and that is different from selling nothing.
    row.update(sold_units=None, sold_per_week=None, weekly_units=None)
    if sold is not None and weeks:
        row.update(sales_row(sold, variant_id, store['id'], weeks))
    return row


def option_values(variant):
    return [text(variant.get('option1_value')), text(variant.get('option2_value')),
            text(variant.get('option3_value'))]


def option_labels(item):
    return [text(item.get('option1_name')), text(item.get('option2_name')),
            text(item.get('option3_name'))]


def build(stores, categories, items, inventory, mapping, money, sold=None, sales=None, trading=None):
    store_rows, unmatched_mapping = index_stores(stores, mapping)
    levels = index_inventory(inventory)
    category_names = {}
    for category in categories:
        category_id = text(category.get('id'))
        if category_id:
            category_names[category_id] = text(category.get('name'))
    built, variant_ids = [], set()
    for item in items:
        if text(item.get('deleted_at')):
            continue
        item_id = text(item.get('id'))
        if not item_id:
            raise ValueError('A Loyverse item has no id.')
        track_stock = item.get('track_stock') is True
        is_composite = item.get('is_composite') is True
        # A composite item without production holds its components' stock, not its own.
        components_only = is_composite and item.get('use_production') is not True
        category_id = text(item.get('category_id'))
        variants = []
        for variant in item.get('variants') or []:
            if text(variant.get('deleted_at')):
                continue
            variant_id = text(variant.get('variant_id'))
            if not variant_id:
                raise ValueError('A Loyverse variant has no id.')
            if variant_id in variant_ids:
                raise ValueError('Duplicate Loyverse variant id.')
            variant_ids.add(variant_id)
            entries = {}
            for entry in variant.get('stores') or []:
                entry_store = text(entry.get('store_id'))
                if not entry_store:
                    continue
                if entry_store in entries:
                    raise ValueError('Duplicate store settings for one variant.')
                entries[entry_store] = entry
            variants.append({
                'variant_id': variant_id,
                'sku': text(variant.get('sku')),
                'barcode': text(variant.get('barcode')),
                'options': option_values(variant),
                'cost': digits(number(variant.get('cost'))),
                'default_price': digits(number(variant.get('default_price'))),
                'default_pricing_type': text(variant.get('default_pricing_type')),
                'updated_at': text(variant.get('updated_at')),
                'stores': [variant_store_row(entries.get(store['id']), store, levels, variant_id,
                                             track_stock, components_only, sold,
                                             sales['weeks'] if sales else None)
                           for store in store_rows],
            })
        built.append({
            'id': item_id, 'name': text(item.get('item_name')),
            'category_id': category_id,
            'category_name': category_names.get(category_id) if category_id else None,
            'track_stock': track_stock, 'sold_by_weight': item.get('sold_by_weight') is True,
            'is_composite': is_composite, 'use_production': item.get('use_production') is True,
            'option_names': option_labels(item), 'updated_at': text(item.get('updated_at')),
            'variants': variants,
        })
    built.sort(key=lambda row: ((row['name'] or '').lower(), row['id']))
    return {'schema_version': SCHEMA_VERSION, 'captured_at': now(), 'currency': money,
            'sales': sales, 'performance': trading, 'stores': store_rows,
            'unmatched_store_mapping': unmatched_mapping,
            'categories': sorted(({'id': key, 'name': value} for key, value in category_names.items()),
                                 key=lambda row: (row['name'] or '').lower()),
            'items': built, 'counts': counts(built, store_rows), 'limitations': LIMITATIONS}


def counts(items, store_rows):
    rows = [row for item in items for variant in item['variants'] for row in variant['stores']]
    return {'stores': len(store_rows),
            'mapped_stores': sum(1 for store in store_rows if store['workspace_store']),
            'items': len(items), 'variants': sum(len(item['variants']) for item in items),
            'variant_store_rows': len(rows),
            'tracked': sum(1 for row in rows if row['stock_state'] == 'tracked'),
            'not_tracked': sum(1 for row in rows if row['stock_state'] == 'not_tracked'),
            'components_only': sum(1 for row in rows if row['stock_state'] == 'components_only'),
            'unknown_stock': sum(1 for row in rows if row['stock_state'] == 'unknown'),
            'below_optimal': sum(1 for row in rows if row['below_optimal'] is not None),
            'low_stock_alerts': sum(1 for row in rows if row['low_stock_alert']),
            'optimal_stock_set': sum(1 for row in rows if row['optimal_stock'] is not None),
            'unavailable': sum(1 for row in rows if row['available_for_sale'] is False),
            'with_sales': sum(1 for row in rows if row['sold_units'] is not None
                              and Decimal(row['sold_units']) > 0),
            'no_sales': sum(1 for row in rows if row['sold_units'] is not None
                            and Decimal(row['sold_units']) <= 0)}


def bounded(name, fallback, ceiling):
    try:
        return max(0, min(ceiling, int(os.environ.get(name, fallback))))
    except ValueError:
        return int(fallback)


def since(stamp):
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(stamp)).total_seconds()
    except (TypeError, ValueError):
        return None


def visible_stores(catalogue, user):
    """Owners see every Loyverse store. Others see only their assigned, mapped stores."""
    if user['role'] == 'owner':
        return [store['id'] for store in catalogue['stores']]
    return [store['id'] for store in catalogue['stores'] if store['workspace_store'] in user['stores']]


def scope(catalogue, user):
    allowed = set(visible_stores(catalogue, user))
    stores = [store for store in catalogue['stores'] if store['id'] in allowed]
    items = []
    for item in catalogue['items']:
        variants = [dict(variant, stores=[row for row in variant['stores'] if row['store_id'] in allowed])
                    for variant in item['variants']]
        items.append(dict(item, variants=variants))
    trading = catalogue.get('performance')
    if isinstance(trading, dict):
        trading = {key: value for key, value in trading.items() if key in allowed}
    scoped = dict(catalogue, stores=stores, items=items, performance=trading,
                  counts=counts(items, stores))
    if user['role'] != 'owner':
        scoped.pop('unmatched_store_mapping', None)
    return scoped


def status_row(row):
    if not row:
        return None
    return {'status': row['status'], 'started_at': row['started_at'],
            'finished_at': row['finished_at'], 'error': row['error']}


def state():
    if not enabled():
        return 'not_connected'
    return 'ready' if token() else 'credential_missing'


def latest(user):
    with connect() as db:
        stored = db.execute('''SELECT * FROM loyverse_syncs WHERE status='complete' AND payload IS NOT NULL
          ORDER BY started_at DESC LIMIT 1''').fetchone()
        last = db.execute('SELECT * FROM loyverse_syncs ORDER BY started_at DESC LIMIT 1').fetchone()
    result = {'connection': state(), 'can_refresh': user['role'] in ('owner', 'manager'),
              'last_attempt': status_row(last), 'catalogue': None, 'captured_at': None}
    if stored:
        catalogue = json.loads(stored['payload'])
        result['catalogue'] = scope(catalogue, user)
        result['captured_at'] = catalogue['captured_at']
    return result


def system_actor():
    """A non-login account, so a scheduled read is still attributable."""
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT id,name,email,role,stores FROM users WHERE email=?',
                         (SYSTEM_ACTOR_EMAIL,)).fetchone()
        if row:
            return {'id': row['id'], 'name': row['name'], 'email': row['email'],
                    'role': row['role'], 'stores': json.loads(row['stores'])}
        actor_id = secrets.token_hex(16)
        # The plaintext is generated and immediately discarded: nothing can match this hash.
        db.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?)',
                   (actor_id, SYSTEM_ACTOR_EMAIL, 'Scheduled sync',
                    password_hash(secrets.token_urlsafe(64)), 'staff', json.dumps([]), now()))
        audit(db, actor_id, 'loyverse.schedule_identity_created')
        return {'id': actor_id, 'name': 'Scheduled sync', 'email': SYSTEM_ACTOR_EMAIL,
                'role': 'staff', 'stores': []}


def sync(actor, scheduled=False):
    """One owner-initiated read. Never scheduled, never a POS write."""
    if not enabled():
        raise HTTPException(503, 'The Loyverse connection is switched off. The technical owner enables it in server configuration.')
    if not token():
        raise HTTPException(503, 'No Loyverse credential is configured on this server. Your collection is unchanged.')
    try:
        store_map()
    except ValueError as problem:
        raise HTTPException(500, str(problem))
    daily = bounded('SH_LOYVERSE_DAILY_SYNCS', '24', 500)
    cooldown = bounded('SH_LOYVERSE_COOLDOWN_SECONDS', '60', 86400)
    run_id, stamp = secrets.token_hex(16), now()
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        stale = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        db.execute('''UPDATE loyverse_syncs SET status='failed',finished_at=?,error=? WHERE status='running' AND started_at<?''',
                   (now(), 'Refresh interrupted; you can try again.', stale))
        if db.execute("SELECT 1 FROM loyverse_syncs WHERE status='running'").fetchone():
            raise HTTPException(409, 'A refresh is already running. Check this page again in a moment.')
        previous = db.execute('''SELECT started_at FROM loyverse_syncs WHERE status='complete'
          ORDER BY started_at DESC LIMIT 1''').fetchone()
        waited = since(previous['started_at']) if previous else None
        # The daily job runs once by definition; the cooldown guards click-spamming.
        if cooldown and not scheduled and waited is not None and waited < cooldown:
            raise HTTPException(429, f'Loyverse was read {int(waited)} seconds ago. Wait {cooldown - int(waited)} seconds before refreshing again.')
        used = db.execute('SELECT COUNT(*) FROM loyverse_syncs WHERE started_at>=?', (stamp[:10],)).fetchone()[0]
        if used >= daily:
            raise HTTPException(429, 'The daily Loyverse refresh limit has been reached. The last saved list is still shown.')
        db.execute('INSERT INTO loyverse_syncs(id,actor_id,started_at,finished_at,status,payload,error,request_count) VALUES (?,?,?,?,?,?,?,?)',
                   (run_id, actor['id'], stamp, None, 'running', None, None, 0))
        audit(db, actor['id'], 'loyverse.refresh_requested' if not scheduled
              else 'loyverse.refresh_requested_on_schedule', None, run_id)
    try:
        catalogue, requests_made = capture()
        payload = json.dumps(catalogue, separators=(',', ':'))
    except HTTPException as refusal:
        fail(actor, run_id, refusal.detail if isinstance(refusal.detail, str) else 'Loyverse refused the request.')
        raise
    except ValueError as problem:
        # Only this module's own checks raise ValueError, and none of those messages
        # interpolate provider content, so reporting one cannot leak account data.
        detail = f'This reader refused the Loyverse response: {problem} Nothing was changed, and the last saved list is still shown.'
        fail(actor, run_id, str(problem))
        raise HTTPException(502, detail)
    except Exception:
        # Other provider bodies can carry account data or the credential; never persist them.
        fail(actor, run_id, 'Loyverse was unreachable or returned something this reader will not accept.')
        raise HTTPException(502, 'The Loyverse list could not be read or verified. Nothing was changed, and the last saved list is still shown.')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('UPDATE loyverse_syncs SET status=?,finished_at=?,payload=?,request_count=? WHERE id=?',
                   ('complete', now(), payload, requests_made, run_id))
        keep = [row['id'] for row in db.execute('''SELECT id FROM loyverse_syncs WHERE payload IS NOT NULL
          ORDER BY started_at DESC LIMIT ?''', (KEEP_PAYLOADS,))]
        for row in db.execute('SELECT id FROM loyverse_syncs WHERE payload IS NOT NULL').fetchall():
            if row['id'] not in keep:
                db.execute('UPDATE loyverse_syncs SET payload=NULL WHERE id=?', (row['id'],))
        surplus = db.execute('SELECT id FROM loyverse_syncs ORDER BY started_at DESC').fetchall()[KEEP_ROWS:]
        for row in surplus:
            db.execute('DELETE FROM loyverse_syncs WHERE id=?', (row['id'],))
        audit(db, actor['id'], 'loyverse.refreshed' if not scheduled else 'loyverse.refreshed_on_schedule',
              None, json.dumps({'run': run_id, 'requests': requests_made, 'items': catalogue['counts']['items'],
                                'variants': catalogue['counts']['variants']}))
    if scheduled:
        return {'status': 'complete', 'run': run_id, 'requests': requests_made,
                'captured_at': catalogue['captured_at'], 'counts': catalogue['counts']}
    return latest(actor)


def fail(actor, run_id, message):
    with connect() as db:
        db.execute('UPDATE loyverse_syncs SET status=?,finished_at=?,error=? WHERE id=?',
                   ('failed', now(), message, run_id))
        audit(db, actor['id'], 'loyverse.refresh_failed', None, run_id)
