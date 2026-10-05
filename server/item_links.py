"""Where a product is bought, recorded by the shop rather than by configuration.

These links are not secrets. They are a public marketplace page per product,
and the people who know which page is right are the people in the shop. Keeping
them in `SH_LOYVERSE_SUPPLIERS` meant every correction needed a hosting login
and a redeploy, which is why they live here instead: the shop records them in
the app, and they take effect on the next read.

A link is still validated before it is stored. Anything that is not a plain
`https://` URL is refused, because this value ends up in an `href` that a person
in the shop will click.

Two slots exist per variant, and the column names predate them: `url` holds the
Shopee page and `lazada_url` the Lazada page. Each is checked against its own
host, so a page from the wrong marketplace cannot be filed under the other. The
table still carries `alternative_name` and `alternative_url` from a third,
freely named slot that was removed; nothing reads or writes them.
"""
import json
from urllib.parse import urlparse

from .db import audit, connect, now

#: A tablet on the counter is paired to a store operator, so an operator has to
#: be able to record a link; that is the person holding the phone in the aisle.
MAY_RECORD = ('owner', 'manager')
MAX_URL = 600
MAX_NAME = 80
MAX_NOTE = 160

#: Two slots are for named marketplaces and are checked against their own hosts.
#: A Lazada page pasted into the Shopee slot would be labelled wrongly in the
#: shop, and the buying ceiling would silently not apply to it.
SHOPEE_HOSTS = ('shopee.ph', 'shp.ee')
LAZADA_HOSTS = ('lazada.com.ph', 'lazada.sg', 'lzd.co')


def host_of(url):
    try:
        return (urlparse(url).hostname or '').lower()
    except ValueError:
        return ''


def from_hosts(url, hosts):
    """Matched on the host itself or a subdomain, so a lookalike does not pass."""
    host = host_of(url)
    return any(host == known or host.endswith('.' + known) for known in hosts)


def clean_url(value, field):
    """Only plain https links. A `javascript:` or `data:` href would be an injection."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if not text.lower().startswith('https://') or len(text) > MAX_URL:
        raise ValueError(f'{field} must be an https link under {MAX_URL} characters.')
    if any(character in text for character in '<>"\'' + chr(10) + chr(13)):
        raise ValueError(f'{field} contains characters that are not allowed in a link.')
    return text


def clean_text(value, field, limit):
    if value is None:
        return None
    text = ' '.join(str(value).split())
    if not text:
        return None
    if len(text) > limit:
        raise ValueError(f'{field} must be under {limit} characters.')
    return text


def row(entry):
    return {'variant_id': entry['variant_id'], 'sku': entry['sku'],
            'item_name': entry['item_name'], 'url': entry['url'],
            'lazada_url': entry['lazada_url'], 'note': entry['note'],
            'updated_at': entry['updated_at'], 'updated_by': entry['updated_by']}


#: Links identified and confirmed with the owner, shipped with the application.
#: They are keyed by SKU because a SKU is what a person reads off the catalogue,
#: and a variant id is not. A link the shop records in the app always wins over
#: one of these; removing a recorded link falls back to the shipped one rather
#: than to nothing, so a shipped link has to be deleted here to stay gone.
SHIPPED = {
    '10437': {'url': 'https://shopee.ph/Kuhne-Mustard-Dijon-185g'
                     '-i.284922593.56757096831',
              'note': 'Kuhne Dijon 185g'},
    '10202': {'url': 'https://shopee.ph/Crying-Thaiger-Sriracha-Wasabi-Chili-Sauce-440mL'
                     '-i.149174871.24283515465',
              'note': 'Crying Thaiger Sriracha Wasabi 440ml'},
    '10245': {'url': 'https://shopee.ph/Sante-Fruit-Muesli-350g'
                     '-i.149174871.14461423123',
              'note': 'Sante Fruit Muesli 350g, the Fruit variant only'},
}


def shipped():
    """The shipped links against today's variant ids, resolved through the catalogue.

    An unknown SKU simply does not appear: a link that cannot be tied to a
    variant is better absent than attached to the wrong one.
    """
    if not SHIPPED:
        return {}
    with connect() as db:
        stored = db.execute("""SELECT payload FROM loyverse_syncs
            WHERE status='complete' AND payload IS NOT NULL
            ORDER BY started_at DESC LIMIT 1""").fetchone()
    if not stored:
        return {}
    catalogue = json.loads(stored['payload'])
    found = {}
    for item in catalogue.get('items') or []:
        for variant in item.get('variants') or []:
            entry = SHIPPED.get(str(variant.get('sku')))
            if not entry:
                continue
            found[variant['variant_id']] = {
                'variant_id': variant['variant_id'], 'sku': variant.get('sku'),
                'item_name': item.get('name'), 'url': entry.get('url'),
                'lazada_url': entry.get('lazada_url'), 'note': entry.get('note'),
                'updated_at': catalogue.get('captured_at'), 'updated_by': 'shipped'}
    return found


def listing():
    """Every link for a variant: what the shop recorded, over what ships with us."""
    with connect() as db:
        recorded = {entry['variant_id']: row(entry)
                    for entry in db.execute('SELECT * FROM item_links')}
    for variant_id, entry in shipped().items():
        recorded.setdefault(variant_id, entry)
    return recorded


def record(user, variant_id, body):
    """Store or replace one product's buying links.

    A record with no link at all is removed rather than kept as an empty row:
    an empty record and no record mean the same thing to every reader, and
    keeping both would let them disagree.
    """
    if user['role'] not in MAY_RECORD:
        raise PermissionError('Only the owner or a manager can record a buying link.')
    url = clean_url(body.get('url'), 'The Shopee link')
    lazada_url = clean_url(body.get('lazada_url'), 'The Lazada link')
    note = clean_text(body.get('note'), 'The note', MAX_NOTE)
    if url and not from_hosts(url, SHOPEE_HOSTS):
        raise ValueError('The Shopee link has to be a shopee.ph page. '
                         'Put a link from anywhere else in the third slot and name it.')
    if lazada_url and not from_hosts(lazada_url, LAZADA_HOSTS):
        raise ValueError('The Lazada link has to be a lazada.com.ph page. '
                         'Put a link from anywhere else in the third slot and name it.')
    if not url and not lazada_url:
        return remove(user, variant_id)
    with connect() as db:
        db.execute('DELETE FROM item_links WHERE variant_id=?', (variant_id,))
        db.execute('''INSERT INTO item_links(variant_id,sku,item_name,url,lazada_url,
                        note,updated_at,updated_by)
                      VALUES (?,?,?,?,?,?,?,?)''',
                   (variant_id, clean_text(body.get('sku'), 'The SKU', MAX_NAME),
                    clean_text(body.get('item_name'), 'The item name', MAX_URL),
                    url, lazada_url, note, now(), user['id']))
        audit(db, user['id'], 'item_link.recorded', variant_id,
              url or lazada_url or '')
        entry = db.execute('SELECT * FROM item_links WHERE variant_id=?', (variant_id,)).fetchone()
    return row(entry)


def remove(user, variant_id):
    if user['role'] not in MAY_RECORD:
        raise PermissionError('Only the owner or a manager can remove a buying link.')
    with connect() as db:
        existing = db.execute('SELECT variant_id FROM item_links WHERE variant_id=?',
                              (variant_id,)).fetchone()
        if not existing:
            return {'ok': True, 'already': True}
        db.execute('DELETE FROM item_links WHERE variant_id=?', (variant_id,))
        audit(db, user['id'], 'item_link.removed', variant_id)
    return {'ok': True, 'already': False}
