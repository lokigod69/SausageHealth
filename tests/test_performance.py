"""Synthetic trading cases only. Reported figures, never reconciled or presented as profit."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from server import performance

STORE = 'store-a'
SECOND = 'store-b'
ZONE = (timezone(timedelta(hours=8)), 8)


def receipt(date, hour=15, total='100', quantity='2', kind='SALE', store_id=STORE,
            variant_id='variant-1', line_total=None, **fields):
    """A receipt whose business date is the given local day and hour at UTC+8."""
    local = datetime.fromisoformat(date + 'T{:02d}:00:00+08:00'.format(hour))
    return {'receipt_type': kind, 'cancelled_at': None, 'store_id': store_id,
            'receipt_date': local.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
            'total_money': Decimal(total), 'total_tax': 0, 'tip': 0, 'surcharge': 0,
            'line_items': [{'variant_id': variant_id, 'quantity': Decimal(quantity),
                            'total_money': Decimal(line_total if line_total is not None else total)}],
            **fields}


def build(receipts, stores=(STORE,)):
    return performance.build(list(receipts), list(stores), zone=ZONE)[STORE]


def test_daily_figures_cover_every_calendar_day_including_quiet_ones():
    block = build([receipt('2026-07-01'), receipt('2026-07-03', total='50', quantity='1')])
    assert [row['date'] for row in block['daily']] == ['2026-07-01', '2026-07-02', '2026-07-03']
    middle = block['daily'][1]
    # A day with no receipts is reported as having none, not asserted to be closed.
    assert middle['receipts'] == 0 and middle['units'] == '0' and middle['collected'] == '0'
    assert block['calendar_days'] == 3 and block['trading_days'] == 2
    assert block['collected'] == '150' and block['units'] == '3'


def test_a_refund_is_subtracted_once_across_every_figure():
    block = build([receipt('2026-07-01', total='100', quantity='2'),
                   receipt('2026-07-01', total='30', quantity='1', kind='REFUND')])
    assert block['collected'] == '70' and block['units'] == '1'
    assert block['receipts'] == 2 and block['refund_receipts'] == 1
    assert block['daily'][0]['collected'] == '70'
    assert block['variants']['variant-1']['units'] == '1'


def test_hours_use_the_stated_local_offset():
    block = build([receipt('2026-07-01', hour=16), receipt('2026-07-01', hour=16),
                   receipt('2026-07-02', hour=9)])
    slots = {(row['weekday_name'], row['hour']): row['receipts'] for row in block['hourly']}
    assert slots[('Wed', 16)] == 2 and slots[('Thu', 9)] == 1
    assert block['local_utc_offset_hours'] == 8


def test_cancelled_unknown_and_foreign_receipts_are_counted_apart():
    receipts = [receipt('2026-07-01'),
                dict(receipt('2026-07-01'), cancelled_at='2026-07-02T00:00:00Z'),
                receipt('2026-07-01', kind='SOMETHING_ELSE'),
                receipt('2026-07-01', store_id='store-zzz'),
                dict(receipt('2026-07-01'), receipt_date=None)]
    block = build(receipts)
    assert block['receipts'] == 1
    assert block['skipped'] == {'cancelled': 1, 'other_type': 1, 'unknown_store': 1, 'no_date': 1}


def test_stores_never_share_figures():
    receipts = [receipt('2026-07-01', total='100', store_id=STORE),
                receipt('2026-07-01', total='900', store_id=SECOND)]
    blocks = performance.build(receipts, [STORE, SECOND], zone=ZONE)
    assert blocks[STORE]['collected'] == '100' and blocks[SECOND]['collected'] == '900'


def test_basket_and_concentration_are_derived_from_what_was_recorded():
    receipts = [receipt('2026-07-01', total='100', quantity='2', variant_id='a', line_total='100'),
                receipt('2026-07-02', total='300', quantity='1', variant_id='b', line_total='300')]
    block = build(receipts)
    assert block['basket']['average_collected'] == '200.00'
    assert block['basket']['average_units'] == '1.50'
    assert block['basket']['average_lines'] == '1.00'
    # Two variants only, so the top ten is everything.
    assert block['concentration']['top_ten_share'] == '100.0'


def test_first_and_last_sold_are_tracked_per_variant():
    block = build([receipt('2026-07-01', variant_id='a'), receipt('2026-07-20', variant_id='a'),
                   receipt('2026-07-05', variant_id='b')])
    assert block['variants']['a']['first_sold'] == '2026-07-01'
    assert block['variants']['a']['last_sold'] == '2026-07-20'
    assert block['variants']['b']['first_sold'] == block['variants']['b']['last_sold'] == '2026-07-05'


def test_tax_tip_and_surcharge_are_flagged_rather_than_silently_summed():
    block = build([receipt('2026-07-01'), dict(receipt('2026-07-02'), total_tax=Decimal('5'))])
    assert block['money_flags'] == {'total_tax': 1}
    clean = build([receipt('2026-07-01')])
    assert clean['money_flags'] == {}


def test_floats_and_non_finite_money_are_refused():
    with pytest.raises(ValueError):
        build([dict(receipt('2026-07-01'), total_money=100.5)])
    with pytest.raises(ValueError):
        build([dict(receipt('2026-07-01'), total_money=Decimal('NaN'))])


def test_marked_periods_are_flagged_on_the_days_they_cover(monkeypatch):
    monkeypatch.setenv('SH_LOYVERSE_EXCLUDED_PERIODS',
                       '[{"from":"2026-07-02","to":"2026-07-03","reason":"Renovation"}]')
    block = build([receipt('2026-07-01'), receipt('2026-07-04')])
    flags = {row['date']: row['excluded'] for row in block['daily']}
    assert flags == {'2026-07-01': False, '2026-07-02': True,
                     '2026-07-03': True, '2026-07-04': False}
    assert block['excluded_periods'][0]['reason'] == 'Renovation'


def test_a_broken_excluded_period_is_refused_rather_than_ignored(monkeypatch):
    for bad in ('not json', '{"from":"a"}', '[{"from":"2026-07-02"}]',
                '[{"from":"2026-07-09","to":"2026-07-02"}]', '[{"from":"x","to":"y"}]'):
        monkeypatch.setenv('SH_LOYVERSE_EXCLUDED_PERIODS', bad)
        with pytest.raises(ValueError):
            performance.excluded_periods()
    monkeypatch.delenv('SH_LOYVERSE_EXCLUDED_PERIODS')
    assert performance.excluded_periods() == []


def test_an_account_with_no_receipts_reports_emptiness_without_dividing_by_zero():
    block = build([])
    assert block['receipts'] == 0 and block['daily'] == [] and block['trading_days'] == 0
    assert block['concentration']['top_ten_share'] is None
    assert block['from'] is None and block['to'] is None
