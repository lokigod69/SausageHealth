"""Read-only CSV analysis. All business outputs must go to private storage, never Git."""
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

VERSION = 'loyverse-csv-review/1'
MONEY = ('Gross sales', 'Discounts', 'Net sales', 'Taxes', 'Total collected', 'Cost of goods', 'Gross profit')
SHARED = ('Name', 'Category', 'Sold by weight', 'Track stock')


def number(value, field, optional=False):
    if value == '' and optional:
        return None
    try:
        result = Decimal(value)
    except (InvalidOperation, ValueError):
        raise ValueError(f'Invalid number in {field}') from None
    if not result.is_finite():
        raise ValueError(f'Non-finite number in {field}')
    return result


def money(value):
    return format(value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP), 'f')


def load_csv(path, required):
    raw = Path(path).read_bytes()
    with Path(path).open(encoding='utf-8-sig', newline='') as source:
        reader = csv.DictReader(source, strict=True)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)) or not set(required) <= set(headers):
            raise ValueError('Missing or duplicate CSV headers')
        rows = list(reader)
    if not rows or any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError('Empty or ragged CSV records')
    return rows, {'filename': Path(path).name, 'sha256': hashlib.sha256(raw).hexdigest(),
                  'bytes': len(raw), 'records': len(rows), 'headers': headers}


def analyze_items(path):
    rows, source = load_csv(path, ('Handle', 'SKU', *SHARED, 'Cost'))
    store_names = [key[len('In stock ['):-1] for key in source['headers'] if key.startswith('In stock [') and key.endswith(']')]
    if not store_names:
        raise ValueError('No store-specific stock columns')
    if any(row.get('SKU of included item') for row in rows):
        raise ValueError('Composite component rows need a separate mapping; do not count them as SKUs')
    groups = defaultdict(list)
    for record, row in enumerate(rows, 2):
        if not row['SKU'] or not row['Handle']:
            raise ValueError('Missing SKU or handle')
        groups[row['Handle']].append((record, row))
    if len({row['SKU'] for row in rows}) != len(rows):
        raise ValueError('Duplicate SKU')
    normalized = []
    for handle, group in groups.items():
        common, origins = {}, {}
        for field in SHARED:
            populated = [(record, row[field]) for record, row in group if row[field]]
            values = {value for _, value in populated}
            if len(values) > 1:
                raise ValueError(f'Conflicting shared {field} within a handle')
            common[field] = next(iter(values), '')
            origins[field] = populated[0][0] if populated else None
        if not common['Name']:
            raise ValueError('Handle has no product name')
        for field in ('Sold by weight', 'Track stock'):
            if common[field] not in ('Y', 'N', ''):
                raise ValueError(f'Unexpected {field} flag')
        for record, row in group:
            options = [row.get(f'Option {index} value', '') for index in range(1, 4)]
            variant = ', '.join(value for value in options if value)
            cost = number(row['Cost'], 'Cost', optional=True)
            item = {'record': record, 'handle': handle, 'sku': row['SKU'], 'name': common['Name'],
                'variant': variant, 'category': common['Category'] or None, 'shared_field_records': origins,
                'sold_by_weight': common['Sold by weight'] or None, 'track_stock': common['Track stock'] or None,
                'cost': str(cost) if cost is not None else None, 'stores': {}}
            for store in store_names:
                fields = {label: row[f'{label} [{store}]'] for label in ('Available for sale', 'Price', 'In stock', 'Low stock')}
                if fields['Available for sale'] not in ('Y', 'N', ''):
                    raise ValueError('Unexpected availability flag')
                variable_price = fields['Price'].lower() == 'variable'
                values = {label: None if label == 'Price' and variable_price else number(fields[label], label, optional=True)
                          for label in ('Price', 'In stock', 'Low stock')}
                item['stores'][store] = {label: str(value) if value is not None else None for label, value in values.items()}
                item['stores'][store]['available'] = fields['Available for sale'] or None
                item['stores'][store]['price_kind'] = 'variable' if variable_price else 'missing' if values['Price'] is None else 'fixed'
            normalized.append(item)
    summary = {'source': source, 'base_products': len(groups), 'sku_rows': len(normalized),
        'blank_names_resolved_within_handle': sum(not row['Name'] for row in rows),
        'zero_cost_skus': sum(item['cost'] is not None and Decimal(item['cost']) == 0 for item in normalized),
        'missing_cost_skus': sum(item['cost'] is None for item in normalized),
        'uncategorized_skus': sum(item['category'] is None for item in normalized),
        'categories': dict(Counter(item['category'] or 'Uncategorized' for item in normalized)),
        'stores': {}}
    for store in store_names:
        summary['stores'][store] = {name: sum(predicate(item, item['stores'][store]) for item in normalized) for name, predicate in {
            'available_skus': lambda i, v: v['available'] == 'Y',
            'tracked_skus': lambda i, v: i['track_stock'] == 'Y',
            'untracked_skus': lambda i, v: i['track_stock'] == 'N',
            'negative_recorded_stock_skus': lambda i, v: v['In stock'] is not None and Decimal(v['In stock']) < 0,
            'zero_recorded_stock_skus': lambda i, v: v['In stock'] is not None and Decimal(v['In stock']) == 0,
            'missing_stock_skus': lambda i, v: v['In stock'] is None,
            'variable_price_skus': lambda i, v: v['price_kind'] == 'variable',
            'price_below_recorded_positive_cost_skus': lambda i, v: i['cost'] is not None and v['Price'] is not None and Decimal(i['cost']) > 0 and Decimal(v['Price']) < Decimal(i['cost']),
        }.items()}
    return summary, normalized


def analyze_receipts(path):
    rows, source = load_csv(path, ('Date', 'Receipt number', 'Receipt type', 'Store', 'POS', 'Status', 'Payment type', *MONEY))
    parsed, seen = [], set()
    for record, row in enumerate(rows, 2):
        key = (row['Store'], row['POS'], row['Receipt number'])
        if not all(key) or key in seen:
            raise ValueError('Missing or duplicate store/POS/receipt key')
        seen.add(key)
        if row['Receipt type'] not in ('Sale', 'Refund') or row['Status'] != 'Closed':
            raise ValueError('Unsupported receipt type/status; review before aggregation')
        values = {field: number(row[field], field) for field in MONEY}
        expected_sign = 1 if row['Receipt type'] == 'Sale' else -1
        if any(expected_sign * values[field] < 0 for field in ('Gross sales', 'Discounts', 'Net sales', 'Total collected', 'Cost of goods')):
            raise ValueError('Unexpected sale/refund signs; do not guess the convention')
        stamp = datetime.strptime(row['Date'], '%d/%m/%Y %H:%M')
        parsed.append({'record': record, 'receipt': row['Receipt number'], 'store': row['Store'], 'type': row['Receipt type'],
            'stamp': stamp, 'payment': row['Payment type'], 'values': values})
    def totals(subset):
        return {field: money(sum((row['values'][field] for row in subset), Decimal(0))) for field in MONEY}
    issues = []
    for row in parsed:
        v = row['values']
        for field, delta in [('net = gross - discounts', v['Net sales'] - v['Gross sales'] + v['Discounts']),
                             ('collected = net + taxes', v['Total collected'] - v['Net sales'] - v['Taxes']),
                             ('gross profit = net - recorded cost', v['Gross profit'] - v['Net sales'] + v['Cost of goods'])]:
            if delta:
                issues.append({'record': row['record'], 'equation': field, 'difference': str(delta)})
    summary = {'source': source, 'date_format': 'DD/MM/YYYY HH:mm', 'timezone': 'Not embedded in export',
        'currency': 'Not embedded in export; PHP unconfirmed', 'export_filters': 'Not verified',
        'refund_convention': 'Already negative in source; sum once without negating again',
        'arithmetic_issues': issues, 'stores': {}}
    for store in sorted({row['store'] for row in parsed}):
        selected = [row for row in parsed if row['store'] == store]
        sales = [row for row in selected if row['type'] == 'Sale']
        refunds = [row for row in selected if row['type'] == 'Refund']
        start, end = min(row['stamp'] for row in selected), max(row['stamp'] for row in selected)
        daily = []
        for offset in range((end.date() - start.date()).days + 1):
            day = start.date() + timedelta(days=offset)
            subset = [row for row in selected if row['stamp'].date() == day]
            daily.append({'date': day.isoformat(), 'receipt_rows': len(subset),
                'sales': sum(row['type'] == 'Sale' for row in subset), 'refunds': sum(row['type'] == 'Refund' for row in subset),
                'net_sales': totals(subset)['Net sales'] if subset else None,
                'coverage': 'No records; not assumed zero' if not subset else 'Boundary date; full day unconfirmed' if day in (start.date(), end.date()) else 'Records present; filter completeness unconfirmed'})
        zero_cost = [row for row in sales if row['values']['Cost of goods'] == 0]
        negative = [row for row in sales if row['values']['Gross profit'] < 0]
        summary['stores'][store] = {'first_record': start.isoformat(' '), 'last_record': end.isoformat(' '),
            'sale_receipts': len(sales), 'refund_receipts': len(refunds), 'signed_totals': totals(selected),
            'sale_totals': totals(sales), 'refund_totals': totals(refunds),
            'average_sale_receipt_net': money(sum((row['values']['Net sales'] for row in sales), Decimal(0)) / len(sales)) if sales else None,
            'zero_recorded_cost_sale_receipts': len(zero_cost), 'zero_cost_sale_net': totals(zero_cost)['Net sales'],
            'negative_reported_gross_profit_sale_receipts': len(negative),
            'discounted_sale_receipts': sum(row['values']['Discounts'] > 0 for row in sales),
            'daily': daily,
            'payments': {payment: {'receipt_rows': len(subset), 'signed_collected': totals(subset)['Total collected']}
                for payment in sorted({row['payment'] for row in selected})
                for subset in [[row for row in selected if row['payment'] == payment]]},
            'cost_review_sample': [{'record': row['record'], 'receipt': row['receipt'], 'date': row['stamp'].isoformat(' '),
                'net_sales': money(row['values']['Net sales']), 'recorded_cost': money(row['values']['Cost of goods']),
                'reported_gross_profit': money(row['values']['Gross profit'])}
                for row in sorted(negative, key=lambda row: row['values']['Gross profit'])[:10]]}
    return summary


def analyze(items, receipts):
    catalog, normalized = analyze_items(items)
    return {'analysis_version': VERSION, 'catalog': catalog, 'receipts': analyze_receipts(receipts), 'normalized_catalog': normalized}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--items', required=True)
    parser.add_argument('--receipts', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    target = Path(args.output).resolve()
    private = Path(__file__).resolve().parents[1] / '.data'
    if not target.is_relative_to(private.resolve()) or target.exists():
        parser.error('Choose a new output file inside the ignored .data directory.')
    result = analyze(args.items, args.receipts)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('Private analysis written; originals unchanged.')
