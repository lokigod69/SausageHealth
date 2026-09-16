"""Supplier lead times and when a product has to be reordered.

The supplier registry is configuration, never source code: supplier names,
rhythms and lead times are commercially sensitive and this repository is public.
It is read from `SH_LOYVERSE_SUPPLIERS`, which is encrypted at rest by the host.

Two kinds of supplier exist here and they behave differently:

  * A **lead time** supplier delivers some number of days after an order. Ordering
    a day later simply arrives a day later.
  * A **cycle** supplier only takes orders on one weekday and delivers on another.
    Missing the order day does not cost a day, it costs a whole cycle, so the
    useful figure is the order deadline rather than an average lead time.

Nothing here invents a supplier. A product no rule matches is reported as
unassigned and gets no reordering advice at all, because advice without a known
lead time would be a guess dressed as a recommendation.
"""
import json
import os
from datetime import date, timedelta
from urllib.parse import quote

WEEKDAYS = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')


def weekday_number(value):
    if isinstance(value, int) and 0 <= value <= 6:
        return value
    if isinstance(value, str) and value.strip().lower() in WEEKDAYS:
        return WEEKDAYS.index(value.strip().lower())
    raise ValueError('A weekday must be Monday to Sunday, or 0 to 6.')


def whole_days(value, field):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 120:
        raise ValueError(f'{field} must be a whole number of days from 0 to 120.')
    return value


def safe_url(value, field):
    """Only plain https links. A javascript: or data: href would be an injection."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if not text.lower().startswith('https://') or len(text) > 600:
        raise ValueError(f'{field} must be an https link under 600 characters.')
    if any(character in text for character in '<>"\'' + chr(10) + chr(13)):
        raise ValueError(f'{field} contains characters that are not allowed in a link.')
    return text


def parse_alternatives(raw, field):
    out = []
    for entry in raw or []:
        if not isinstance(entry, dict) or not entry.get('name'):
            raise ValueError(f'Every entry in {field} needs a name.')
        template = entry.get('search_url')
        if template:
            safe_url(str(template).replace('{query}', 'x'), field + '.search_url')
            if '{query}' not in str(template):
                raise ValueError(f'{field}.search_url must contain {{query}}.')
        out.append({'name': str(entry['name'])[:60],
                    'url': safe_url(entry.get('url'), field + '.url'),
                    'search_url': str(template) if template else None,
                    'note': str(entry.get('note') or '')[:120] or None})
    return out


def registry():
    """Parsed supplier configuration, or None when none is set."""
    raw = os.environ.get('SH_LOYVERSE_SUPPLIERS', '').strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except ValueError:
        raise ValueError('SH_LOYVERSE_SUPPLIERS is not valid JSON.')
    if not isinstance(parsed, dict):
        raise ValueError('SH_LOYVERSE_SUPPLIERS must be an object.')
    suppliers = {}
    for entry in parsed.get('suppliers') or []:
        if not isinstance(entry, dict) or not entry.get('id') or not entry.get('name'):
            raise ValueError('Every supplier needs an id and a name.')
        supplier = {'id': str(entry['id']), 'name': str(entry['name'])[:80],
                    'note': str(entry.get('note') or '')[:200] or None,
                    'buffer_days': whole_days(entry.get('buffer_days', 0), 'buffer_days'),
                    'search_url': None, 'alternatives': parse_alternatives(
                        entry.get('alternatives'), 'supplier alternatives')}
        template = entry.get('search_url')
        if template:
            checked = safe_url(str(template).replace('{query}', 'x'), 'search_url')
            if checked is None or '{query}' not in str(template):
                raise ValueError('search_url must be an https link containing {query}.')
            supplier['search_url'] = str(template)
        cycle = entry.get('cycle')
        if cycle is not None:
            if not isinstance(cycle, dict):
                raise ValueError('A supplier cycle must be an object.')
            supplier['cycle'] = {
                'order_weekday': weekday_number(cycle.get('order_weekday')),
                'delivery_weekday': weekday_number(cycle.get('delivery_weekday')),
                'week_offset': whole_days(cycle.get('week_offset', 0), 'week_offset')}
            supplier['lead_days'] = None
        else:
            lead = entry.get('lead_days')
            if isinstance(lead, dict):
                low = whole_days(lead.get('min'), 'lead_days.min')
                high = whole_days(lead.get('max'), 'lead_days.max')
                if high < low:
                    raise ValueError('lead_days.max cannot be smaller than lead_days.min.')
                supplier['lead_days'] = {'min': low, 'max': high}
            elif lead is None:
                raise ValueError(f"Supplier {supplier['id']} needs lead_days or a cycle.")
            else:
                days = whole_days(lead, 'lead_days')
                supplier['lead_days'] = {'min': days, 'max': days}
            supplier['cycle'] = None
        if supplier['id'] in suppliers:
            raise ValueError('Duplicate supplier id: ' + supplier['id'])
        suppliers[supplier['id']] = supplier
    rules = []
    for rule in parsed.get('rules') or []:
        if not isinstance(rule, dict) or rule.get('supplier') not in suppliers:
            raise ValueError('Every rule needs a supplier that exists in the registry.')
        match = rule.get('match')
        if not isinstance(match, dict) or not any(
                match.get(key) for key in ('category', 'name_contains', 'name_exact')):
            raise ValueError('Every rule needs a category, name_contains or name_exact match.')
        rules.append({
            'supplier': rule['supplier'],
            'category': str(match['category']) if match.get('category') else None,
            'name_contains': str(match['name_contains']).lower() if match.get('name_contains') else None,
            'name_exact': str(match['name_exact']).lower() if match.get('name_exact') else None,
            'alternative': rule.get('alternative') if rule.get('alternative') in suppliers else None,
        })
    links = {}
    for key, entry in (parsed.get('links') or {}).items():
        if not isinstance(entry, dict):
            raise ValueError('Every link entry must be an object.')
        links[str(key).strip().lower()] = {
            'url': safe_url(entry.get('url'), 'link url'),
            'note': str(entry.get('note') or '')[:120] or None,
            'alternatives': parse_alternatives(entry.get('alternatives'), 'link alternatives')}
    if not suppliers:
        raise ValueError('SH_LOYVERSE_SUPPLIERS lists no suppliers.')
    return {'suppliers': suppliers, 'rules': rules, 'links': links}


def match(rules, item_name, category_name):
    """First matching rule wins, so put the specific ones first."""
    name = (item_name or '').lower()
    category = category_name or ''
    for rule in rules:
        if rule['name_exact'] and name == rule['name_exact']:
            return rule
        if rule['name_contains'] and rule['name_contains'] in name:
            return rule
        if rule['category'] and rule['category'] == category:
            return rule
    return None


def next_delivery(today, cycle):
    """The next order day this supplier accepts, and when that order arrives."""
    ahead = (cycle['order_weekday'] - today.weekday()) % 7
    order_day = today + timedelta(days=ahead)
    to_delivery = (cycle['delivery_weekday'] - order_day.weekday()) % 7
    delivery = order_day + timedelta(days=to_delivery + 7 * cycle['week_offset'])
    return order_day, delivery


def plan(supplier, today, cover_days):
    """When this product must be ordered, given how long the stock lasts.

    `cover_days` is None whenever the stock or the sales rate is unknown. In that
    case there is no honest deadline to give, so none is given.
    """
    result = {'supplier_id': supplier['id'], 'supplier_name': supplier['name'],
              'supplier_note': supplier['note'], 'buffer_days': supplier['buffer_days'],
              'cycle': None, 'lead_days': None, 'next_order_day': None,
              'arrives': None, 'order_by': None, 'status': 'unknown', 'days_of_cover': None}
    if supplier['cycle']:
        order_day, delivery = next_delivery(today, supplier['cycle'])
        result['cycle'] = True
        result['next_order_day'] = order_day.isoformat()
        result['arrives'] = delivery.isoformat()
        lead = (delivery - today).days
        result['lead_days'] = {'min': lead, 'max': lead}
    else:
        result['cycle'] = False
        result['lead_days'] = dict(supplier['lead_days'])
    if cover_days is None:
        return result
    result['days_of_cover'] = round(cover_days, 1)
    # Plan against the slowest the supplier has been, plus any deliberate buffer.
    needed = result['lead_days']['max'] + supplier['buffer_days']
    if cover_days <= 0:
        result['status'] = 'out_of_stock'
    elif cover_days <= needed:
        result['status'] = 'order_now'
    else:
        result['order_by'] = (today + timedelta(days=int(cover_days - needed))).isoformat()
        result['status'] = 'ok'
    if supplier['cycle']:
        # A cycle supplier cannot be ordered from on an arbitrary day. Skipping an
        # order day does not cost a day, it costs a whole cycle, so the honest
        # deadline is the last order day whose delivery still beats the runout.
        runout = today + timedelta(days=int(cover_days) - supplier['buffer_days'])
        deadline, probe = None, today
        for _ in range(8):
            order_day, delivery = next_delivery(probe, supplier['cycle'])
            if delivery > runout:
                break
            deadline, probe = order_day, order_day + timedelta(days=1)
        if cover_days <= 0:
            result['status'] = 'out_of_stock'
            result['order_by'] = result['next_order_day']
        elif deadline is None:
            # Even the next order day arrives too late; ordering it is still the best move.
            result['status'] = 'order_now'
            result['order_by'] = result['next_order_day']
        elif deadline == today:
            result['status'] = 'order_now'
            result['order_by'] = deadline.isoformat()
        else:
            result['status'] = 'ok'
            result['order_by'] = deadline.isoformat()
    return result


def assign(items, today, config=None):
    """Supplier and reorder plan per variant and store, plus what nothing matched."""
    config = config if config is not None else registry()
    if not config:
        return None
    assignments, unassigned = {}, []
    for item in items:
        rule = match(config['rules'], item.get('name'), item.get('category_name'))
        for variant in item.get('variants') or []:
            for row in variant.get('stores') or []:
                key = (variant['variant_id'], row['store_id'])
                if not rule:
                    unassigned.append({'item': item.get('name'), 'variant_id': variant['variant_id'],
                                       'category': item.get('category_name')})
                    continue
                supplier = config['suppliers'][rule['supplier']]
                entry = plan(supplier, today, cover(row))
                if rule['alternative']:
                    other = config['suppliers'][rule['alternative']]
                    entry['alternative_name'] = other['name']
                    entry['alternative_lead_days'] = other['lead_days']
                entry.update(buying_links(config, supplier, variant, item))
                assignments[key] = entry
    seen = {row['variant_id'] for row in unassigned}
    return {'assignments': assignments,
            'unassigned': sorted(({'item': row['item'], 'category': row['category']}
                                  for row in unassigned if row['variant_id'] in seen),
                                 key=lambda row: (row['category'] or '', row['item'] or ''))[:200],
            'unassigned_count': len(seen),
            'suppliers': sorted(config['suppliers'].values(), key=lambda row: row['name'])}


def buying_links(config, supplier, variant, item):
    """An exact listing when one is recorded, otherwise a search at that supplier.

    A search link is explicitly marked as a search: it finds candidates, it does
    not identify the listing the shop actually buys from.
    """
    name = (item.get('name') or '').strip()
    recorded = None
    for key in (variant.get('sku'), name):
        if key and str(key).strip().lower() in config.get('links', {}):
            recorded = config['links'][str(key).strip().lower()]
            break
    result = {'buy_url': None, 'buy_kind': None, 'buy_note': None,
              'other_sources': list(supplier.get('alternatives') or [])}
    if recorded and recorded['url']:
        result.update(buy_url=recorded['url'], buy_kind='listing', buy_note=recorded['note'])
    elif supplier.get('search_url') and name:
        result.update(buy_url=supplier['search_url'].replace('{query}', quote(name)),
                      buy_kind='search')
    if recorded:
        result['other_sources'] = list(recorded['alternatives']) + result['other_sources']
    resolved = []
    for source in result['other_sources']:
        url = source.get('url')
        if not url and source.get('search_url') and name:
            url = source['search_url'].replace('{query}', quote(name))
        resolved.append({'name': source['name'], 'url': url, 'note': source.get('note')})
    result['other_sources'] = resolved
    return result


def cover(row):
    """Days the stock lasts at the recent weekly rate, when both are known."""
    if row.get('stock_state') != 'tracked' or row.get('in_stock') is None:
        return None
    rate = row.get('sold_per_week')
    if rate is None:
        return None
    try:
        weekly = float(rate)
        stock = float(row['in_stock'])
    except (TypeError, ValueError):
        return None
    if weekly <= 0:
        return None
    return stock / (weekly / 7)


def today_local(offset_hours):
    from datetime import datetime, timezone
    return datetime.now(timezone(timedelta(hours=offset_hours))).date()
