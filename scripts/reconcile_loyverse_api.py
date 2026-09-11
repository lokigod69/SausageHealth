"""Offline source comparison; no network, database, credential or POS writes.

This first contract covers closed, zero-tax receipts without tips or surcharges.
Other cases require a separately validated mapping, never an assumed net amount.
Parse API JSON with parse_float=Decimal before calling this module.
"""
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal

VERSION = 'loyverse-api-comparison/1'
FIELDS = ('Gross sales', 'Discounts', 'Net sales', 'Taxes', 'Total collected', 'Cost of goods', 'Gross profit')


def exact(value):
    if isinstance(value, (bool, float)) or value is None:
        raise ValueError('Expected an exact source number, not float/bool/missing')
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError('Non-finite source number')
    return result


def unique_index(rows, key):
    indexed = {}
    for row in rows:
        identity = key(row)
        parts = identity if isinstance(identity, tuple) else (identity,)
        if any(part in (None, '') for part in parts) or identity in indexed:
            raise ValueError('Missing or duplicate source identity')
        indexed[identity] = row
    return indexed


def utc(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.utcoffset() != timedelta(0):
        raise ValueError('Expected a UTC API timestamp')
    return parsed


def receipt_values(receipt):
    kind = receipt['receipt_type']
    if kind not in {'SALE', 'REFUND'} or receipt.get('cancelled_at') is not None:
        raise ValueError('Unsupported receipt type/cancellation')
    if any(exact(receipt[field]) != 0 for field in ('total_tax', 'tip', 'surcharge')):
        raise ValueError('Tax/tip/surcharge mapping needs separate validation')
    lines = receipt['line_items']
    unique_index(lines, lambda line: line['id'])
    if not lines or any(line.get('line_taxes') for line in lines):
        raise ValueError('Empty receipt or tax mapping needs separate validation')
    for line in lines:
        for field in ('quantity', 'price', 'gross_total_money', 'total_money', 'cost', 'cost_total', 'total_discount'):
            if exact(line[field]) < 0:
                raise ValueError('Unexpected API sign; do not double-normalize refunds')
    gross = sum((exact(line['gross_total_money']) for line in lines), Decimal(0))
    line_net = sum((exact(line['total_money']) for line in lines), Decimal(0))
    cost = sum((exact(line['cost_total']) for line in lines), Decimal(0))
    discount = exact(receipt['total_discount'])
    collected = exact(receipt['total_money'])
    if discount < 0 or collected < 0:
        raise ValueError('Unexpected API sign; do not double-normalize refunds')
    payment_total = sum((exact(payment['money_amount']) for payment in receipt['payments']), Decimal(0))
    if line_net != collected or payment_total != collected or gross - discount != collected:
        raise ValueError('Receipt/line/payment arithmetic does not reconcile')
    if sum((exact(line['total_discount']) for line in lines), Decimal(0)) != discount:
        raise ValueError('Line discounts do not reconcile')
    sign = -1 if kind == 'REFUND' else 1
    values = (gross, discount, collected, Decimal(0), collected, cost, collected - cost)
    return dict(zip(FIELDS, (value * sign for value in values)))


def reconcile(csv_rows, api_receipts, stores, local_offset_hours=8):
    """Compare identities and observed values; never add overlapping snapshots.

    Timestamp agreement tests a stated fixed offset. It does not confirm the
    store's configured timezone, filters, complete trading days or cash deposits.
    """
    store_by_name = unique_index(stores, lambda store: store['name'])
    unique_index(stores, lambda store: store['id'])
    api = unique_index(api_receipts, lambda row: (row['store_id'], row['receipt_number']))
    csv = unique_index(csv_rows, lambda row: (store_by_name[row['Store']]['id'], row['Receipt number']))
    api_values = {key: receipt_values(row) for key, row in api.items()}
    matched = sorted(set(csv) & set(api))
    differences, references = [], []
    minute_matches = 0
    totals = {field: Decimal(0) for field in FIELDS}
    for key in matched:
        original, live = csv[key], api[key]
        issues = []
        if original['Status'] != 'Closed' or original['Receipt type'].upper() != live['receipt_type']:
            issues.append('type/status')
        for field in FIELDS:
            if exact(original[field]) != api_values[key][field]:
                issues.append(field)
            totals[field] += api_values[key][field]
        api_minute = utc(live['receipt_date']).astimezone(timezone(timedelta(hours=local_offset_hours))).strftime('%d/%m/%Y %H:%M')
        if api_minute == original['Date']:
            minute_matches += 1
        else:
            issues.append('receipt_date at candidate offset')
        reference = {'store_id': key[0], 'receipt_number': key[1], 'line_count': len(live['line_items'])}
        references.append(reference)
        if issues:
            differences.append({**reference, 'fields': issues})
    return {
        'version': VERSION, 'matched_receipts': len(matched),
        'matched_line_rows': sum(len(api[key]['line_items']) for key in matched),
        'matched_types': dict(Counter(api[key]['receipt_type'] for key in matched)),
        'missing_from_api': [list(key) for key in sorted(set(csv) - set(api))],
        'api_only': [list(key) for key in sorted(set(api) - set(csv))],
        'differences': differences, 'candidate_utc_offset_hours': local_offset_hours,
        'matching_local_minutes': minute_matches,
        'matched_signed_source_totals': {field: str(value) for field, value in totals.items()},
        'matched_references': references,
        'limitations': ['Source comparison, not a financial ledger or verified profit.',
                       'Matched receipt identities are overlaps, not additional sales.',
                       'This mapping covers zero-tax receipts without tips/surcharges only.',
                       'Timestamp agreement does not certify the configured timezone or complete trading days.'],
    }
