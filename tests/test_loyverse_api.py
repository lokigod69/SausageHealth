"""Synthetic comparison cases only; live business data and credentials stay private."""
from copy import deepcopy
from decimal import Decimal
import pytest
from scripts.reconcile_loyverse_api import reconcile, receipt_values


def source(kind='SALE', number='r1'):
    return {'store_id': 'test-store', 'receipt_number': number, 'receipt_type': kind,
        'cancelled_at': None, 'receipt_date': '2026-08-14T01:00:29Z',
        'total_tax': 0, 'tip': 0, 'surcharge': 0, 'total_discount': Decimal('0.10'),
        'total_money': Decimal('10.10'), 'payments': [{'money_amount': Decimal('10.10')}],
        'line_items': [{'id': 'line1', 'sku': '001', 'quantity': 1, 'price': Decimal('10.20'),
            'gross_total_money': Decimal('10.20'), 'total_money': Decimal('10.10'),
            'cost': Decimal('3.03'), 'cost_total': Decimal('3.03'),
            'total_discount': Decimal('0.10'), 'line_taxes': []}]}


def csv_row(kind='Sale', number='r1'):
    sign = -1 if kind == 'Refund' else 1
    return {'Store': 'Test', 'Receipt number': number, 'Receipt type': kind,
        'Status': 'Closed', 'Date': '14/08/2026 09:00',
        **{key: str(sign * Decimal(value)) for key, value in {
            'Gross sales': '10.20', 'Discounts': '.10', 'Net sales': '10.10',
            'Taxes': '0', 'Total collected': '10.10', 'Cost of goods': '3.03', 'Gross profit': '7.07'}.items()}}


STORES = [{'id': 'test-store', 'name': 'Test'}]


def test_refunds_normalize_once_and_overlaps_are_not_new_sales():
    result = reconcile([csv_row(), csv_row('Refund','r2')],
        [source(), source('REFUND','r2'), source(number='later')], STORES)
    assert result['matched_receipts'] == 2 and result['matched_line_rows'] == 2
    assert Decimal(result['matched_signed_source_totals']['Net sales']) == 0
    assert result['api_only'] == [['test-store', 'later']]
    assert result['matching_local_minutes'] == 2 and result['differences'] == []


def test_amount_and_date_differences_remain_visible():
    row = csv_row(); row['Net sales'] = '10.11'; row['Date'] = '14/08/2026 10:00'
    result = reconcile([row, csv_row(number='missing')], [source()], STORES)
    assert result['differences'][0]['fields'] == ['Net sales', 'receipt_date at candidate offset']
    assert result['missing_from_api'] == [['test-store', 'missing']]


def test_duplicate_receipt_line_or_store_keys_do_not_silently_overwrite():
    with pytest.raises(ValueError, match='duplicate'):
        reconcile([csv_row()], [source(),source()], STORES)
    receipt = source(); receipt['line_items'].append(deepcopy(receipt['line_items'][0]))
    with pytest.raises(ValueError, match='duplicate'):
        receipt_values(receipt)
    with pytest.raises(ValueError, match='duplicate'):
        reconcile([csv_row()], [source()], STORES + [{'id':'second', 'name':'Test'}])


@pytest.mark.parametrize('field,value', [('total_tax',1), ('tip',1), ('surcharge',1),
    ('cancelled_at','2026-08-15T01:00:00Z'), ('total_money',-1), ('total_money',Decimal('NaN')),
    ('total_money',10.1)])
def test_unvalidated_semantics_or_numbers_require_review(field, value):
    receipt = source(); receipt[field] = value
    with pytest.raises(ValueError):
        receipt_values(receipt)


def test_receipt_lines_and_payments_must_balance():
    receipt = source(); receipt['payments'][0]['money_amount'] = Decimal('9.99')
    with pytest.raises(ValueError, match='arithmetic'):
        receipt_values(receipt)
