"""Suppliers the shop records itself, on top of the configured ones.

Configuration is not replaced. `SH_LOYVERSE_SUPPLIERS` still holds the
suppliers that were set up with the deployment, and nothing already there stops
working. This module only lets the shop add to them, because the alternative
was that adding a supplier required a hosting login and a redeploy -- and the
person who knows a new supplier's number is standing in the shop.

Where both describe the same thing the shop's record wins: its rules are tried
before the configured ones, and a record reusing a configured supplier's id
replaces it. The shop can correct its own entry in seconds; configuration
cannot, so configuration is the staler of the two by construction.

Validation is not duplicated. A record is turned back into the same shape the
configuration variable has and handed to `suppliers.parse`, so a lead time
typed on a tablet is checked exactly as strictly as one pasted into the host.
"""
import re

from . import suppliers as rules
from .db import audit, connect, now

MAY_RECORD = ('owner', 'manager')
MAX_NAME = 80
MAX_NOTE = 200
#: One matching line per product or category, as a person would write a list.
MAX_LINES = 60
MAX_LINE = 120

FIELDS = ('name', 'lead_min', 'lead_max', 'buffer_days', 'order_weekday', 'delivery_weekday',
          'week_offset', 'whatsapp', 'viber', 'messenger', 'person', 'note',
          'match_names', 'match_categories')


def slug(value):
    """A stable id from the name, so the shop never has to invent one."""
    made = re.sub(r'[^a-z0-9]+', '-', str(value or '').strip().lower()).strip('-')
    if not made:
        raise ValueError('A supplier needs a name with letters or digits in it.')
    return made[:40]


def lines(value, field):
    """A textarea of match terms, one per line, emptied of blanks and duplicates."""
    if value is None:
        return []
    seen, kept = set(), []
    for line in str(value).splitlines():
        text = ' '.join(line.split())
        if not text or text.lower() in seen:
            continue
        if len(text) > MAX_LINE:
            raise ValueError(f'{field} has a line longer than {MAX_LINE} characters.')
        seen.add(text.lower())
        kept.append(text)
    if len(kept) > MAX_LINES:
        raise ValueError(f'{field} can hold at most {MAX_LINES} lines.')
    return kept


def row(entry):
    return {key: entry[key] for key in ('id',) + FIELDS} | {
        'updated_at': entry['updated_at'], 'updated_by': entry['updated_by']}


def listing():
    with connect() as db:
        return [row(entry) for entry in
                db.execute('SELECT * FROM shop_suppliers ORDER BY name')]


def as_config(rows):
    """The shop's records in the shape the configuration variable uses.

    Every rule names the supplier it was recorded under, so a rule can never
    point at a supplier that is not in this same object.
    """
    made = {'suppliers': [], 'rules': []}
    for entry in rows:
        supplier = {'id': entry['id'], 'name': entry['name'],
                    'note': entry['note'],
                    'buffer_days': entry['buffer_days'] or 0,
                    'contact': {'whatsapp': entry['whatsapp'], 'viber': entry['viber'],
                                'messenger': entry['messenger'], 'person': entry['person']}}
        if entry['order_weekday'] and entry['delivery_weekday']:
            supplier['cycle'] = {'order_weekday': entry['order_weekday'],
                                 'delivery_weekday': entry['delivery_weekday'],
                                 'week_offset': entry['week_offset'] or 0}
        else:
            supplier['lead_days'] = {'min': entry['lead_min'], 'max': entry['lead_max']}
        made['suppliers'].append(supplier)
        for name in lines(entry['match_names'], 'Products'):
            made['rules'].append({'supplier': entry['id'], 'match': {'name_contains': name}})
        for category in lines(entry['match_categories'], 'Categories'):
            made['rules'].append({'supplier': entry['id'], 'match': {'category': category}})
    return made


def merged(config=None):
    """The configured registry with the shop's own records laid over it."""
    rows = listing()
    if not rows:
        return config
    own = rules.parse(as_config(rows))
    if not config:
        return own
    return {'suppliers': {**config['suppliers'], **own['suppliers']},
            # The shop's rules are tried first, so a configured mapping that is
            # wrong can be corrected without a deploy.
            'rules': own['rules'] + config['rules'],
            'links': {**(config.get('links') or {}), **(own.get('links') or {})}}


def record(user, body):
    """Store or replace one supplier the shop records itself."""
    if user['role'] not in MAY_RECORD:
        raise PermissionError('Only the owner or a manager can record a supplier.')
    name = ' '.join(str(body.get('name') or '').split())[:MAX_NAME]
    identifier = str(body.get('id') or '').strip() or slug(name)
    entry = {
        'id': slug(identifier), 'name': name,
        'lead_min': body.get('lead_min'), 'lead_max': body.get('lead_max'),
        'buffer_days': body.get('buffer_days') or 0,
        'order_weekday': (body.get('order_weekday') or '').strip().lower() or None,
        'delivery_weekday': (body.get('delivery_weekday') or '').strip().lower() or None,
        'week_offset': body.get('week_offset') or 0,
        # Normalised here, not only validated: a wa.me link needs bare digits, and
        # storing the raw text would leave the record and the reorder plan
        # disagreeing about the same number.
        'whatsapp': rules.phone(body.get('whatsapp'), 'WhatsApp number'),
        'viber': rules.phone(body.get('viber'), 'Viber number'),
        'messenger': rules.safe_url(body.get('messenger'), 'The Messenger link'),
        'person': ' '.join(str(body.get('person') or '').split())[:60] or None,
        'note': ' '.join(str(body.get('note') or '').split())[:MAX_NOTE] or None,
        'match_names': '\n'.join(lines(body.get('match_names'), 'Products')) or None,
        'match_categories': '\n'.join(lines(body.get('match_categories'), 'Categories')) or None,
    }
    if entry['order_weekday'] or entry['delivery_weekday']:
        if not (entry['order_weekday'] and entry['delivery_weekday']):
            raise ValueError('A weekday cycle needs both an order day and a delivery day.')
    elif entry['lead_min'] is None and entry['lead_max'] is None:
        raise ValueError('Give either a lead time in days or an order and delivery weekday.')
    else:
        if entry['lead_min'] is None:
            entry['lead_min'] = entry['lead_max']
        if entry['lead_max'] is None:
            entry['lead_max'] = entry['lead_min']
    # Parsing it as a registry is the validation: the same rules as configuration.
    rules.parse(as_config([entry]))
    with connect() as db:
        db.execute('DELETE FROM shop_suppliers WHERE id=?', (entry['id'],))
        db.execute(f'''INSERT INTO shop_suppliers(id,{",".join(FIELDS)},updated_at,updated_by)
                       VALUES ({",".join("?" * (len(FIELDS) + 3))})''',
                   (entry['id'], *(entry[key] for key in FIELDS), now(), user['id']))
        audit(db, user['id'], 'supplier.recorded', entry['id'], entry['name'])
        saved = db.execute('SELECT * FROM shop_suppliers WHERE id=?', (entry['id'],)).fetchone()
    return row(saved)


def from_parsed(supplier, own_rules):
    """One validated supplier, back as the row this table holds.

    Anything this table cannot hold is refused by name rather than dropped. An
    import that silently loses a search link or an alternative source would
    leave the shop with a supplier that looks right and orders from nowhere.
    """
    for field, label in (('search_url', 'a search link'),
                         ('alternatives', 'alternative sources')):
        if supplier.get(field):
            raise ValueError(
                f"'{supplier['name']}' carries {label}, which this import cannot store. "
                'Leave that supplier in the hosting configuration, where it already works.')
    names, categories = [], []
    for rule in own_rules:
        if rule['name_exact']:
            raise ValueError(
                f"A rule for '{supplier['name']}' matches an exact name, which this import "
                'cannot store. Use a name fragment instead, or leave it in configuration.')
        if rule['alternative']:
            raise ValueError(
                f"A rule for '{supplier['name']}' names a second supplier to fall back on, "
                'which this import cannot store. Leave it in configuration.')
        if rule['name_contains']:
            names.append(rule['name_contains'])
        if rule['category']:
            categories.append(rule['category'])
    cycle = supplier.get('cycle')
    lead = supplier.get('lead_days')
    return {
        'id': supplier['id'], 'name': supplier['name'],
        'lead_min': lead['min'] if lead else None,
        'lead_max': lead['max'] if lead else None,
        'buffer_days': supplier.get('buffer_days') or 0,
        'order_weekday': rules.WEEKDAYS[cycle['order_weekday']] if cycle else None,
        'delivery_weekday': rules.WEEKDAYS[cycle['delivery_weekday']] if cycle else None,
        'week_offset': cycle['week_offset'] if cycle else 0,
        'whatsapp': supplier['contact']['whatsapp'], 'viber': supplier['contact']['viber'],
        'messenger': supplier['contact']['messenger'],
        'person': supplier['contact']['person'], 'note': supplier.get('note'),
        'match_names': '\n'.join(names) or None,
        'match_categories': '\n'.join(categories) or None,
    }


def import_many(user, text):
    """Several suppliers at once, in the shape the configuration variable uses.

    This exists so nobody has to type a list of suppliers in by hand. It is the
    same validation as a single record, because the payload is parsed as a
    registry first; nothing is written unless every supplier in it is accepted.
    """
    import json
    if user['role'] not in MAY_RECORD:
        raise PermissionError('Only the owner or a manager can import suppliers.')
    try:
        payload = json.loads(text)
    except ValueError:
        raise ValueError('That is not valid JSON. Paste the whole object, braces included.')
    if not isinstance(payload, dict) or not payload.get('suppliers'):
        raise ValueError('The object needs a "suppliers" list.')
    parsed = rules.parse(payload)
    entries = [from_parsed(supplier, [rule for rule in parsed['rules']
                                      if rule['supplier'] == supplier['id']])
               for supplier in parsed['suppliers'].values()]
    with connect() as db:
        for entry in entries:
            db.execute('DELETE FROM shop_suppliers WHERE id=?', (entry['id'],))
            db.execute(f'''INSERT INTO shop_suppliers(id,{",".join(FIELDS)},updated_at,updated_by)
                           VALUES ({",".join("?" * (len(FIELDS) + 3))})''',
                       (entry['id'], *(entry[key] for key in FIELDS), now(), user['id']))
            audit(db, user['id'], 'supplier.imported', entry['id'], entry['name'])
    return listing()


def remove(user, supplier_id):
    if user['role'] not in MAY_RECORD:
        raise PermissionError('Only the owner or a manager can remove a supplier.')
    with connect() as db:
        existing = db.execute('SELECT id FROM shop_suppliers WHERE id=?',
                              (supplier_id,)).fetchone()
        if not existing:
            return {'ok': True, 'already': True}
        db.execute('DELETE FROM shop_suppliers WHERE id=?', (supplier_id,))
        audit(db, user['id'], 'supplier.removed', supplier_id)
    return {'ok': True, 'already': False}
