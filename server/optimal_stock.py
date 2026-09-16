"""Work out the optimal stock a shop should hold, from observed sales and lead time.

This module only calculates. It performs no network call and writes nothing; the
numbers it produces are reviewed before anything reaches the POS.

Two rules decide the daily rate, and both matter:

  * Only days that actually traded count, and days the owner marked as
    unrepresentative are removed from both the units and the day count. A
    renovation fortnight left in would quietly lower every target.
  * A product with no observed sales gets no target at all. There is no demand to
    size against, and inventing one would put a number into the POS that no
    evidence supports.

The cover period is the lead time, not the calendar. For a supplier that delivers
N days after an order, cover is N. For a supplier that only accepts orders on one
weekday, cover is the whole cycle plus the pipeline: you must hold enough to reach
the delivery after next, because missing an order day costs a week, not a day.
That figure must not depend on which weekday the calculation happens to run.
"""
import math
from datetime import date, timedelta


def clean_days(daily, excluded):
    """Business dates that traded and were not marked unrepresentative."""
    out = set()
    for row in daily:
        if row.get('receipts', 0) <= 0:
            continue
        day = row['date']
        if any(period['from'] <= day <= period['to'] for period in excluded or []):
            continue
        out.add(day)
    return out


def daily_rate(units_by_day, days):
    """Units per trading day, counting only the days supplied."""
    if not days:
        return None
    total = sum(float(units_by_day.get(day, 0)) for day in days)
    return total / len(days)


def cycle_cover_days(cycle):
    """Worst case hold for a weekday-bound supplier, independent of today.

    An order placed on the order day arrives after `pipeline` days. The next
    chance to order is a whole week later, so the stock has to last the pipeline
    plus that week.
    """
    order_to_delivery = (cycle['delivery_weekday'] - cycle['order_weekday']) % 7
    pipeline = order_to_delivery + 7 * cycle['week_offset']
    return pipeline + 7


def cover_days(supplier):
    """How many days of demand a target has to carry for this supplier."""
    if supplier.get('cycle'):
        return cycle_cover_days(supplier['cycle']) + supplier.get('buffer_days', 0)
    lead = supplier.get('lead_days') or {}
    return lead.get('max', 0) + supplier.get('buffer_days', 0)


def target_for(rate, supplier):
    """A whole number of units, at least one for anything that sells at all."""
    if rate is None or rate <= 0:
        return None
    return max(1, math.ceil(rate * cover_days(supplier)))


def plan(rows):
    """Turn per-variant observations into proposed targets, with reasons for skips.

    Each row needs: variant_id, item_id, item, sku, supplier (the registry entry),
    rate (units per trading day or None), tracked (bool), current (existing target).
    """
    proposed, skipped = [], {'no_sales': 0, 'not_tracked': 0, 'no_supplier': 0, 'unchanged': 0}
    for row in rows:
        if row.get('supplier') is None:
            skipped['no_supplier'] += 1
            continue
        if not row.get('tracked'):
            skipped['not_tracked'] += 1
            continue
        target = target_for(row.get('rate'), row['supplier'])
        if target is None:
            skipped['no_sales'] += 1
            continue
        current = row.get('current')
        if current is not None and float(current) == float(target):
            skipped['unchanged'] += 1
            continue
        proposed.append({
            'variant_id': row['variant_id'], 'item_id': row['item_id'],
            'item': row.get('item'), 'sku': row.get('sku'),
            'supplier': row['supplier']['name'], 'cover_days': cover_days(row['supplier']),
            'rate_per_day': round(row['rate'], 3), 'current': current, 'target': target,
        })
    proposed.sort(key=lambda entry: -entry['target'])
    return {'proposed': proposed, 'skipped': skipped,
            'total_units': sum(entry['target'] for entry in proposed)}
