"""Synthetic supplier cases only. No real supplier name appears in this repository."""
import json
from datetime import date

import pytest

from server import suppliers

CONFIG = {
    'suppliers': [
        {'id': 'fast', 'name': 'Fast Co', 'lead_days': 2},
        {'id': 'slow', 'name': 'Slow Co', 'lead_days': {'min': 3, 'max': 7}, 'buffer_days': 7},
        {'id': 'sameday', 'name': 'Same Day Co', 'lead_days': 0},
        {'id': 'weekly', 'name': 'Weekly Co',
         'cycle': {'order_weekday': 'wednesday', 'delivery_weekday': 'friday', 'week_offset': 1}},
    ],
    'rules': [
        {'match': {'name_contains': 'bratwurst'}, 'supplier': 'fast'},
        {'match': {'category': 'Steaks'}, 'supplier': 'slow'},
        {'match': {'category': 'Poultry'}, 'supplier': 'slow', 'alternative': 'sameday'},
        {'match': {'category': 'Cold Cuts'}, 'supplier': 'weekly'},
    ],
}


def configured(monkeypatch, config=None):
    monkeypatch.setenv('SH_LOYVERSE_SUPPLIERS', json.dumps(config or CONFIG))
    return suppliers.registry()


def row(in_stock='14', per_week='7', state='tracked', store_id='store-a'):
    return {'store_id': store_id, 'stock_state': state, 'in_stock': in_stock,
            'sold_per_week': per_week}


def item(name='Plain Item', category='Sausages', rows=None, variant_id='v1'):
    """A neutral name by default, so a category test is not caught by a name rule."""
    return {'name': name, 'category_name': category,
            'variants': [{'variant_id': variant_id, 'stores': rows or [row()]}]}


def test_a_lead_time_supplier_gives_a_deadline_from_the_slowest_case(monkeypatch):
    config = configured(monkeypatch)
    # 14 in stock at 7 a week is 14 days of cover; Fast Co needs 2.
    result = suppliers.assign([item(name='Bratwurst (Classic)')], date(2026, 9, 16), config)
    entry = result['assignments'][('v1', 'store-a')]
    assert entry['supplier_name'] == 'Fast Co'
    assert entry['days_of_cover'] == 14.0 and entry['status'] == 'ok'
    assert entry['order_by'] == '2026-09-28'


def test_a_buffer_brings_the_deadline_forward(monkeypatch):
    config = configured(monkeypatch)
    # Slow Co is 7 days at worst plus a deliberate 7 day buffer, so 14 days of
    # cover is exactly the trigger rather than comfortable.
    result = suppliers.assign([item(category='Steaks')], date(2026, 9, 16), config)
    entry = result['assignments'][('v1', 'store-a')]
    assert entry['supplier_name'] == 'Slow Co' and entry['buffer_days'] == 7
    assert entry['status'] == 'order_now'


def test_out_of_stock_is_its_own_state(monkeypatch):
    config = configured(monkeypatch)
    result = suppliers.assign([item(name='Bratwurst', rows=[row(in_stock='0')])],
                              date(2026, 9, 16), config)
    assert result['assignments'][('v1', 'store-a')]['status'] == 'out_of_stock'


def test_a_cycle_supplier_reports_the_order_day_not_an_average(monkeypatch):
    config = configured(monkeypatch)
    # 16 September 2026 is a Wednesday, so the next order day is today and the
    # delivery is the Friday of the following week.
    result = suppliers.assign([item(category='Cold Cuts')], date(2026, 9, 16), config)
    entry = result['assignments'][('v1', 'store-a')]
    assert entry['cycle'] is True
    assert entry['next_order_day'] == '2026-09-16' and entry['arrives'] == '2026-09-25'
    assert entry['lead_days'] == {'min': 9, 'max': 9}


def test_a_cycle_deadline_moves_to_the_order_day_when_stock_will_not_last(monkeypatch):
    config = configured(monkeypatch)
    # Ten days of cover, but the next cycle delivery is nine days out: ordering
    # on the next order day is the last chance, so it is not "fine for now".
    rows = [row(in_stock='10', per_week='7')]
    result = suppliers.assign([item(category='Cold Cuts', rows=rows)], date(2026, 9, 16), config)
    entry = result['assignments'][('v1', 'store-a')]
    assert entry['status'] == 'order_now' and entry['order_by'] == '2026-09-16'


def test_a_cycle_that_still_has_slack_names_the_later_order_day(monkeypatch):
    config = configured(monkeypatch)
    # Plenty of cover: the deadline is a future order day, not today.
    rows = [row(in_stock='70', per_week='7')]
    result = suppliers.assign([item(category='Cold Cuts', rows=rows)], date(2026, 9, 16), config)
    entry = result['assignments'][('v1', 'store-a')]
    assert entry['status'] == 'ok' and entry['order_by'] > '2026-09-16'


def test_an_order_day_that_has_passed_this_week_rolls_to_the_next(monkeypatch):
    config = configured(monkeypatch)
    # 17 September 2026 is a Thursday, one day after the order day.
    order_day, delivery = suppliers.next_delivery(
        date(2026, 9, 17), config['suppliers']['weekly']['cycle'])
    assert order_day == date(2026, 9, 23) and delivery == date(2026, 10, 2)


def test_a_second_source_is_carried_alongside_the_first(monkeypatch):
    config = configured(monkeypatch)
    result = suppliers.assign([item(category='Poultry')], date(2026, 9, 16), config)
    entry = result['assignments'][('v1', 'store-a')]
    assert entry['supplier_name'] == 'Slow Co'
    assert entry['alternative_name'] == 'Same Day Co'
    assert entry['alternative_lead_days'] == {'min': 0, 'max': 0}


def test_unknown_stock_or_rate_gives_no_deadline_at_all(monkeypatch):
    config = configured(monkeypatch)
    for rows in ([row(state='not_tracked')], [row(in_stock=None)], [row(per_week=None)],
                 [row(per_week='0')]):
        result = suppliers.assign([item(name='Bratwurst', rows=rows)], date(2026, 9, 16), config)
        entry = result['assignments'][('v1', 'store-a')]
        assert entry['days_of_cover'] is None and entry['status'] == 'unknown'
        assert entry['order_by'] is None
        # The supplier is still known even when the timing is not.
        assert entry['supplier_name'] == 'Fast Co'


def test_a_product_no_rule_matches_is_reported_rather_than_guessed(monkeypatch):
    config = configured(monkeypatch)
    result = suppliers.assign(
        [item(name='Mystery Jam', category='Pantry'), item(name='Bratwurst', variant_id='v2')],
        date(2026, 9, 16), config)
    assert result['unassigned_count'] == 1
    assert result['unassigned'][0]['item'] == 'Mystery Jam'
    assert ('v1', 'store-a') not in result['assignments']
    assert ('v2', 'store-a') in result['assignments']


def test_the_first_matching_rule_wins_so_specific_rules_go_first(monkeypatch):
    config = configured(monkeypatch)
    # A bratwurst filed under Steaks still belongs to the name rule listed first.
    result = suppliers.assign([item(name='Veal Bratwurst', category='Steaks')],
                              date(2026, 9, 16), config)
    assert result['assignments'][('v1', 'store-a')]['supplier_name'] == 'Fast Co'


def test_broken_configuration_is_refused_rather_than_half_applied(monkeypatch):
    for bad in (
        'not json',
        '[]',
        json.dumps({'suppliers': [{'id': 'a'}], 'rules': []}),
        json.dumps({'suppliers': [{'id': 'a', 'name': 'A'}], 'rules': []}),
        json.dumps({'suppliers': [{'id': 'a', 'name': 'A', 'lead_days': -1}], 'rules': []}),
        json.dumps({'suppliers': [{'id': 'a', 'name': 'A', 'lead_days': {'min': 5, 'max': 2}}]}),
        json.dumps({'suppliers': [{'id': 'a', 'name': 'A', 'lead_days': 1},
                                  {'id': 'a', 'name': 'B', 'lead_days': 1}]}),
        json.dumps({'suppliers': [{'id': 'a', 'name': 'A', 'lead_days': 1}],
                    'rules': [{'match': {'category': 'X'}, 'supplier': 'missing'}]}),
        json.dumps({'suppliers': [{'id': 'a', 'name': 'A', 'lead_days': 1}],
                    'rules': [{'match': {}, 'supplier': 'a'}]}),
        json.dumps({'suppliers': [{'id': 'a', 'name': 'A',
                                   'cycle': {'order_weekday': 'funday', 'delivery_weekday': 1}}]}),
    ):
        monkeypatch.setenv('SH_LOYVERSE_SUPPLIERS', bad)
        with pytest.raises(ValueError):
            suppliers.registry()


def test_no_configuration_means_no_advice_not_a_default(monkeypatch):
    monkeypatch.delenv('SH_LOYVERSE_SUPPLIERS', raising=False)
    assert suppliers.registry() is None
    assert suppliers.assign([item()], date(2026, 9, 16)) is None
