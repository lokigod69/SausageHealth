"""Trading figures derived from receipts. Read-only, and reported rather than reconciled.

Everything here is an observation of what the POS recorded. None of it is
reconciled against cash, bank or settlement, and none of it is profit: the only
money field used is the amount each receipt says was collected.

Rules this module keeps:
  * A refund arrives as a positive magnitude and the sign is applied once.
  * Cancelled receipts and unknown receipt types are counted apart, never folded in.
  * A calendar day with no receipts is reported as having none. That is not the
    same as a day the shop was closed, and it is not claimed to be.
  * Local hours use a stated UTC offset. Earlier reconciliation matched UTC+8,
    but the store's configured timezone is still unconfirmed upstream.
  * Money that carries tax, tip or surcharge is flagged, because the mapping this
    project validated covers receipts without them.
"""
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

LOCAL_OFFSET_HOURS = 8
WEEKDAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')


def digits(value):
    return None if value is None else format(value, 'f')


def local_zone():
    try:
        hours = int(os.environ.get('SH_LOYVERSE_UTC_OFFSET_HOURS', LOCAL_OFFSET_HOURS))
    except ValueError:
        hours = LOCAL_OFFSET_HOURS
    if not -14 <= hours <= 14:
        raise ValueError('SH_LOYVERSE_UTC_OFFSET_HOURS must be a real UTC offset.')
    return timezone(timedelta(hours=hours)), hours


def excluded_periods():
    """Spans the owner has marked as not representative, such as a renovation."""
    raw = os.environ.get('SH_LOYVERSE_EXCLUDED_PERIODS', '').strip()
    if not raw:
        return []
    try:
        periods = json.loads(raw)
    except ValueError:
        raise ValueError('SH_LOYVERSE_EXCLUDED_PERIODS is not valid JSON.')
    if not isinstance(periods, list):
        raise ValueError('SH_LOYVERSE_EXCLUDED_PERIODS must be a list.')
    cleaned = []
    for period in periods:
        if not isinstance(period, dict) or not period.get('from') or not period.get('to'):
            raise ValueError('Each excluded period needs "from" and "to" dates.')
        for key in ('from', 'to'):
            try:
                datetime.strptime(period[key], '%Y-%m-%d')
            except (TypeError, ValueError):
                raise ValueError('Excluded period dates must look like 2026-09-01.')
        if period['from'] > period['to']:
            raise ValueError('An excluded period ends before it starts.')
        cleaned.append({'from': period['from'], 'to': period['to'],
                        'reason': str(period.get('reason') or 'Marked as not representative')[:160]})
    return cleaned


def exact(value):
    if value is None:
        return Decimal(0)
    if isinstance(value, (bool, float)):
        raise ValueError('Expected an exact source number, not float/bool')
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError('Non-finite source number')
    return result


def build(receipts, store_ids, zone=None):
    """One block of trading figures per store, keyed by store id."""
    zone, offset = zone or local_zone()
    periods = excluded_periods()
    blank = lambda: {
        'receipts': 0, 'refund_receipts': 0, 'units': Decimal(0), 'collected': Decimal(0),
        'lines': 0, 'daily': defaultdict(lambda: {'receipts': 0, 'units': Decimal(0),
                                                  'collected': Decimal(0)}),
        'hourly': defaultdict(lambda: {'receipts': 0, 'units': Decimal(0), 'collected': Decimal(0)}),
        'variants': defaultdict(lambda: {'units': Decimal(0), 'collected': Decimal(0),
                                         'receipts': 0, 'first': None, 'last': None}),
        'money_flags': defaultdict(int), 'first': None, 'last': None,
    }
    per_store = {store_id: blank() for store_id in store_ids}
    skipped = {'cancelled': 0, 'other_type': 0, 'unknown_store': 0, 'no_date': 0}

    for receipt in receipts:
        if receipt.get('cancelled_at'):
            skipped['cancelled'] += 1
            continue
        kind = receipt.get('receipt_type')
        if kind not in ('SALE', 'REFUND'):
            skipped['other_type'] += 1
            continue
        store_id = receipt.get('store_id')
        if store_id not in per_store:
            skipped['unknown_store'] += 1
            continue
        stamp = receipt.get('receipt_date')
        if not stamp:
            skipped['no_date'] += 1
            continue
        moment = datetime.fromisoformat(str(stamp).replace('Z', '+00:00')).astimezone(zone)
        block = per_store[store_id]
        sign = -1 if kind == 'REFUND' else 1
        for field in ('total_tax', 'tip', 'surcharge'):
            if exact(receipt.get(field)) != 0:
                block['money_flags'][field] += 1
        collected = exact(receipt.get('total_money')) * sign
        day = moment.date().isoformat()
        slot = (moment.weekday(), moment.hour)
        units = Decimal(0)
        for line in receipt.get('line_items') or []:
            quantity = exact(line.get('quantity')) * sign
            units += quantity
            variant_id = line.get('variant_id')
            if not variant_id:
                continue
            entry = block['variants'][variant_id]
            entry['units'] += quantity
            entry['collected'] += exact(line.get('total_money')) * sign
            entry['receipts'] += 1
            entry['first'] = day if entry['first'] is None else min(entry['first'], day)
            entry['last'] = day if entry['last'] is None else max(entry['last'], day)
        block['receipts'] += 1
        block['refund_receipts'] += kind == 'REFUND'
        block['units'] += units
        block['collected'] += collected
        block['lines'] += len(receipt.get('line_items') or [])
        for bucket, key in ((block['daily'], day), (block['hourly'], slot)):
            bucket[key]['receipts'] += 1
            bucket[key]['units'] += units
            bucket[key]['collected'] += collected
        block['first'] = day if block['first'] is None else min(block['first'], day)
        block['last'] = day if block['last'] is None else max(block['last'], day)

    return {store_id: shape(block, periods, offset, skipped)
            for store_id, block in per_store.items()}


def calendar(first, last):
    if not first or not last:
        return []
    start = datetime.strptime(first, '%Y-%m-%d').date()
    end = datetime.strptime(last, '%Y-%m-%d').date()
    return [(start + timedelta(days=step)).isoformat() for step in range((end - start).days + 1)]


def in_periods(day, periods):
    return any(period['from'] <= day <= period['to'] for period in periods)


def shape(block, periods, offset, skipped):
    days = calendar(block['first'], block['last'])
    daily = []
    for day in days:
        figures = block['daily'].get(day)
        daily.append({'date': day,
                      'receipts': figures['receipts'] if figures else 0,
                      'units': digits(figures['units'] if figures else Decimal(0)),
                      'collected': digits(figures['collected'] if figures else Decimal(0)),
                      'excluded': in_periods(day, periods)})
    trading_days = sum(1 for row in daily if row['receipts'] > 0)
    hourly = [{'weekday': weekday, 'weekday_name': WEEKDAYS[weekday], 'hour': hour,
               'receipts': figures['receipts'], 'units': digits(figures['units']),
               'collected': digits(figures['collected'])}
              for (weekday, hour), figures in sorted(block['hourly'].items())]
    variants = {variant_id: {'units': digits(entry['units']), 'collected': digits(entry['collected']),
                             'receipts': entry['receipts'], 'first_sold': entry['first'],
                             'last_sold': entry['last']}
                for variant_id, entry in block['variants'].items()}
    ranked = sorted(variants.items(), key=lambda kv: Decimal(kv[1]['collected']), reverse=True)
    top_ten = sum((Decimal(entry['collected']) for _, entry in ranked[:10]), Decimal(0))
    receipts = block['receipts'] or 1
    return {
        'from': block['first'], 'to': block['last'],
        'calendar_days': len(days), 'trading_days': trading_days,
        'receipts': block['receipts'], 'refund_receipts': block['refund_receipts'],
        'units': digits(block['units']), 'collected': digits(block['collected']),
        'lines': block['lines'],
        'basket': {'average_collected': digits((block['collected'] / receipts).quantize(Decimal('0.01'))),
                   'average_lines': digits((Decimal(block['lines']) / receipts).quantize(Decimal('0.01'))),
                   'average_units': digits((block['units'] / receipts).quantize(Decimal('0.01')))},
        'concentration': {'top_ten_collected': digits(top_ten),
                          'top_ten_share': digits((top_ten / block['collected'] * 100).quantize(Decimal('0.1')))
                          if block['collected'] else None},
        'daily': daily, 'hourly': hourly, 'variants': variants,
        'excluded_periods': periods,
        'local_utc_offset_hours': offset,
        'money_flags': dict(block['money_flags']),
        'skipped': skipped,
    }
