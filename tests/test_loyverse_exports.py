"""Synthetic source cases; no business exports or values belong in this suite."""
import csv
import pytest
from scripts.analyze_loyverse_exports import analyze_items, analyze_receipts, MONEY


def write_csv(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def receipt(date='14/08/2026 09:00', receipt_id='r1', kind='Sale', net='10.10'):
    values = {field: '0.00' for field in MONEY}
    for field in ('Gross sales', 'Net sales', 'Total collected', 'Gross profit'):
        values[field] = net
    return {'Date': date, 'Receipt number': receipt_id, 'Receipt type': kind, 'Store': 'Test',
        'POS': 'POS', 'Status': 'Closed', 'Payment type': 'Cash', **values}


def test_signed_refunds_exact_decimals_and_missing_day(tmp_path):
    path = write_csv(tmp_path/'receipts.csv', [receipt(), receipt('16/08/2026 10:00', 'r2', 'Refund', '-1.01')])
    result = analyze_receipts(path)['stores']['Test']
    assert result['signed_totals']['Net sales'] == '9.09'
    assert result['average_sale_receipt_net'] == '10.10'
    assert result['daily'][1]['net_sales'] is None
    assert 'Boundary' in result['daily'][0]['coverage']
    assert result['refund_receipts'] == 1


def test_duplicate_receipts_and_unsigned_refunds_require_review(tmp_path):
    with pytest.raises(ValueError, match='duplicate'):
        analyze_receipts(write_csv(tmp_path/'duplicate.csv', [receipt(), receipt()]))
    with pytest.raises(ValueError, match='signs'):
        analyze_receipts(write_csv(tmp_path/'refund.csv', [receipt(kind='Refund')]))


def test_bad_numbers_and_arithmetic_are_not_hidden(tmp_path):
    bad = receipt()
    bad['Net sales'] = 'NaN'
    with pytest.raises(ValueError, match='Non-finite'):
        analyze_receipts(write_csv(tmp_path/'bad.csv', [bad]))
    bad['Net sales'] = '9.99'
    result = analyze_receipts(write_csv(tmp_path/'mismatch.csv', [bad]))
    assert len(result['arithmetic_issues']) == 3


def item(handle, sku, name, cost='0.00', stock='0'):
    return {'Handle': handle, 'SKU': sku, 'Name': name, 'Category': 'Test' if name else '',
        'Sold by weight': 'N' if name else '', 'Track stock': 'Y' if name else '', 'Cost': cost,
        'Available for sale [Test]': 'Y', 'Price [Test]': '20.00', 'In stock [Test]': stock,
        'Low stock [Test]': '', 'Option 1 value': sku}


def test_variants_share_by_handle_but_never_inherit_cost_or_stock(tmp_path):
    rows = [item('a', '001', 'Product A', '3'), item('b', '002', 'Product B', '4'), item('a', '003', '', '', '')]
    summary, normalized = analyze_items(write_csv(tmp_path/'items.csv', rows))
    variant = next(row for row in normalized if row['sku'] == '003')
    assert summary['base_products'] == 2 and summary['sku_rows'] == 3
    assert variant['name'] == 'Product A' and variant['shared_field_records']['Name'] == 2
    assert variant['cost'] is None and variant['stores']['Test']['In stock'] is None
    assert summary['missing_cost_skus'] == 1
    assert summary['stores']['Test']['zero_recorded_stock_skus'] == 2


def test_ambiguous_catalog_and_composites_are_rejected(tmp_path):
    with pytest.raises(ValueError, match='Conflicting'):
        analyze_items(write_csv(tmp_path/'conflict.csv', [item('a','1','One'), item('a','2','Two')]))
    with pytest.raises(ValueError, match='Duplicate SKU'):
        analyze_items(write_csv(tmp_path/'duplicate.csv', [item('a','1','One'), item('b','1','Two')]))
    with pytest.raises(ValueError, match='Composite'):
        analyze_items(write_csv(tmp_path/'composite.csv', [{**item('a','1','One'), 'SKU of included item':'2'}]))


def test_variable_price_is_not_zero_or_a_false_loss(tmp_path):
    row = {**item('a', '001', 'Variable', '12.50'), 'Price [Test]': 'variable'}
    summary, normalized = analyze_items(write_csv(tmp_path/'variable.csv', [row]))
    assert normalized[0]['stores']['Test']['Price'] is None
    assert normalized[0]['stores']['Test']['price_kind'] == 'variable'
    assert summary['stores']['Test']['price_below_recorded_positive_cost_skus'] == 0
