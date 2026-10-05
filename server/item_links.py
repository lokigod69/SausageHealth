"""Where a product is bought, recorded by the shop rather than by configuration.

These links are not secrets. They are a public marketplace page per product,
and the people who know which page is right are the people in the shop. Keeping
them in `SH_LOYVERSE_SUPPLIERS` meant every correction needed a hosting login
and a redeploy, which is why they live here instead: the shop records them in
the app, and they take effect on the next read.

A link is still validated before it is stored. Anything that is not a plain
`https://` URL is refused, because this value ends up in an `href` that a person
in the shop will click.
"""
from .db import audit, connect, now

#: A tablet on the counter is paired to a store operator, so an operator has to
#: be able to record a link; that is the person holding the phone in the aisle.
MAY_RECORD = ('owner', 'manager')
MAX_URL = 600
MAX_NAME = 80
MAX_NOTE = 160


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
            'alternative_name': entry['alternative_name'],
            'alternative_url': entry['alternative_url'], 'note': entry['note'],
            'updated_at': entry['updated_at'], 'updated_by': entry['updated_by']}


def listing():
    """Every recorded link, keyed by variant so a catalogue read can join them."""
    with connect() as db:
        return {entry['variant_id']: row(entry)
                for entry in db.execute('SELECT * FROM item_links')}


def record(user, variant_id, body):
    """Store or replace one product's buying links.

    A record with no link at all is removed rather than kept as an empty row:
    an empty record and no record mean the same thing to every reader, and
    keeping both would let them disagree.
    """
    if user['role'] not in MAY_RECORD:
        raise PermissionError('Only the owner or a manager can record a buying link.')
    url = clean_url(body.get('url'), 'The shop link')
    alternative_url = clean_url(body.get('alternative_url'), 'The alternative link')
    alternative_name = clean_text(body.get('alternative_name'), 'The alternative source', MAX_NAME)
    note = clean_text(body.get('note'), 'The note', MAX_NOTE)
    if alternative_url and not alternative_name:
        raise ValueError('Name the alternative source, so a reader knows who it is.')
    if not url and not alternative_url:
        return remove(user, variant_id)
    with connect() as db:
        db.execute('DELETE FROM item_links WHERE variant_id=?', (variant_id,))
        db.execute('''INSERT INTO item_links(variant_id,sku,item_name,url,alternative_name,
                        alternative_url,note,updated_at,updated_by)
                      VALUES (?,?,?,?,?,?,?,?,?)''',
                   (variant_id, clean_text(body.get('sku'), 'The SKU', MAX_NAME),
                    clean_text(body.get('item_name'), 'The item name', MAX_URL),
                    url, alternative_name, alternative_url, note, now(), user['id']))
        audit(db, user['id'], 'item_link.recorded', variant_id, url or alternative_url or '')
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
