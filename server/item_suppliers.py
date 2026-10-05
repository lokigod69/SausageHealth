"""Which supplier a product comes from, chosen by hand for one variant.

A match rule guesses a supplier from a product's name or category. That is a
reasonable default for a few hundred items and a poor one for any particular
item: names are inconsistent, categories are broad, and a rule written for one
product sweeps up others. So a choice made here beats every rule, because
somebody holding the product knows better than a string match.

This is a choice per **variant**, not per item: one item can hold two flavours
bought from two different places, which is already true of the buying links.

Nothing here invents a supplier. A choice naming a supplier that no longer
exists is ignored when the plan is built, which falls back to the rules rather
than dropping the product out of ordering altogether.
"""
from .db import audit, connect, now

MAY_CHOOSE = ('owner', 'manager')
#: One screen of the item list at a time, which is what bulk assignment is for.
MAX_AT_ONCE = 500


def listing():
    """Every choice, keyed by variant so a catalogue read can apply them."""
    with connect() as db:
        return {row['variant_id']: row['supplier_id']
                for row in db.execute('SELECT variant_id, supplier_id FROM item_suppliers')}


def rows():
    with connect() as db:
        return [{'variant_id': row['variant_id'], 'supplier_id': row['supplier_id'],
                 'updated_at': row['updated_at'], 'updated_by': row['updated_by']}
                for row in db.execute('SELECT * FROM item_suppliers')]


def choose(user, variant_ids, supplier_id):
    """Point several variants at one supplier, or clear them with no supplier.

    Written as one transaction: a half-applied bulk assignment would leave the
    shop unable to tell which half took.
    """
    if user['role'] not in MAY_CHOOSE:
        raise PermissionError('Only the owner or a manager can choose a supplier.')
    wanted = [str(one).strip() for one in (variant_ids or []) if str(one).strip()]
    if not wanted:
        raise ValueError('Name at least one product to assign.')
    if len(wanted) > MAX_AT_ONCE:
        raise ValueError(f'At most {MAX_AT_ONCE} products at once.')
    supplier = (supplier_id or '').strip() or None
    stamp, actor = now(), user['id']
    with connect() as db:
        for variant_id in wanted:
            db.execute('DELETE FROM item_suppliers WHERE variant_id=?', (variant_id,))
            if supplier:
                db.execute('''INSERT INTO item_suppliers(variant_id,supplier_id,updated_at,updated_by)
                              VALUES (?,?,?,?)''', (variant_id, supplier, stamp, actor))
        # One audit line for the action, not one per product: a bulk assignment
        # is a single decision and reads as one.
        audit(db, actor, 'item_supplier.chosen' if supplier else 'item_supplier.cleared',
              wanted[0] if len(wanted) == 1 else None,
              f'{len(wanted)} product(s)' + (f' to {supplier}' if supplier else ''))
    return {'ok': True, 'count': len(wanted), 'supplier_id': supplier}
