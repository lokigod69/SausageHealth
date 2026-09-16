"""Synthetic cases only. These numbers would be written into a live POS, so the
rules that decide them are pinned here rather than trusted."""
import pytest

from server import optimal_stock as plan


def supplier(lead=None, cycle=None, buffer_days=0, name='Supplier'):
    return {'name': name, 'lead_days': {'min': lead, 'max': lead} if lead is not None else None,
            'cycle': cycle, 'buffer_days': buffer_days}


WEEKLY = {'order_weekday': 2, 'delivery_weekday': 4, 'week_offset': 1}   # Wed -> Fri next week
FRIDAY_MILK = {'order_weekday': 3, 'delivery_weekday': 4, 'week_offset': 0}  # Thu -> Fri


def test_only_trading_days_outside_a_marked_period_are_counted():
    daily = [
        {'date': '2026-08-30', 'receipts': 4},
        {'date': '2026-08-31', 'receipts': 0},     # no receipts at all
        {'date': '2026-09-01', 'receipts': 2},     # inside the marked period
        {'date': '2026-09-13', 'receipts': 5},
    ]
    excluded = [{'from': '2026-09-01', 'to': '2026-09-12'}]
    assert plan.clean_days(daily, excluded) == {'2026-08-30', '2026-09-13'}
    assert plan.clean_days(daily, []) == {'2026-08-30', '2026-09-01', '2026-09-13'}


def test_the_rate_ignores_units_sold_on_excluded_days():
    days = {'2026-08-30', '2026-09-13'}
    units = {'2026-08-30': 6, '2026-09-01': 100, '2026-09-13': 4}
    # The hundred units inside the marked period must not reach the average.
    assert plan.daily_rate(units, days) == 5.0
    assert plan.daily_rate(units, set()) is None


def test_a_weekday_bound_supplier_covers_the_whole_cycle_not_just_the_pipeline():
    # Wednesday order, Friday of the following week: nine days of pipeline, and
    # the next chance to order is a week later, so sixteen days must be held.
    assert plan.cycle_cover_days(WEEKLY) == 16
    # Thursday order, Friday delivery: one day of pipeline plus the week.
    assert plan.cycle_cover_days(FRIDAY_MILK) == 8


def test_cycle_cover_never_depends_on_which_day_the_calculation_runs():
    # The function takes no date at all, which is the point: a standing target
    # cannot be larger because someone happened to recalculate on a Thursday.
    first = plan.cover_days(supplier(cycle=WEEKLY))
    second = plan.cover_days(supplier(cycle=WEEKLY))
    assert first == second == 16


def test_a_lead_time_supplier_uses_its_slowest_case_plus_any_buffer():
    assert plan.cover_days(supplier(lead=3)) == 3
    assert plan.cover_days(supplier(lead=7, buffer_days=7)) == 14
    assert plan.cover_days(supplier(cycle=WEEKLY, buffer_days=2)) == 18


def test_targets_round_up_and_never_fall_below_one():
    assert plan.target_for(2.0, supplier(lead=7)) == 14
    assert plan.target_for(0.01, supplier(lead=2)) == 1
    assert plan.target_for(1.05, supplier(lead=2)) == 3
    assert plan.target_for(0, supplier(lead=2)) is None
    assert plan.target_for(None, supplier(lead=2)) is None


def row(rate=1.0, tracked=True, sup=None, current=None, variant_id='v1'):
    return {'variant_id': variant_id, 'item_id': 'i1', 'item': 'Thing', 'sku': '1',
            'supplier': supplier(lead=7) if sup is None else sup,
            'rate': rate, 'tracked': tracked, 'current': current}


def test_products_without_evidence_or_a_supplier_get_no_target():
    result = plan.plan([
        row(rate=0, variant_id='no-sales'),
        row(rate=None, variant_id='never-sold'),
        row(tracked=False, variant_id='untracked'),
        dict(row(variant_id='no-rule'), supplier=None),
        row(rate=2.0, variant_id='fine'),
    ])
    assert [entry['variant_id'] for entry in result['proposed']] == ['fine']
    assert result['skipped'] == {'no_sales': 2, 'not_tracked': 1,
                                 'no_supplier': 1, 'unchanged': 0}


def test_a_target_that_already_matches_is_not_proposed_again():
    result = plan.plan([row(rate=1.0, current=7), row(rate=1.0, current=3, variant_id='v2')])
    assert result['skipped']['unchanged'] == 1
    assert [entry['variant_id'] for entry in result['proposed']] == ['v2']
    assert result['proposed'][0]['current'] == 3 and result['proposed'][0]['target'] == 7


def test_the_plan_is_ordered_by_size_and_totals_what_it_proposes():
    result = plan.plan([row(rate=0.5, variant_id='small'), row(rate=3.0, variant_id='big')])
    assert [entry['variant_id'] for entry in result['proposed']] == ['big', 'small']
    assert result['total_units'] == 21 + 4
    assert result['proposed'][0]['cover_days'] == 7


@pytest.mark.parametrize('rate,cover,expected', [(5.32, 14, 75), (0.68, 14, 10), (1.053, 7, 8)])
def test_observed_examples_round_the_way_the_shop_would_expect(rate, cover, expected):
    assert plan.target_for(rate, supplier(lead=cover)) == expected
