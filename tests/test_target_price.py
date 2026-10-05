"""A buying ceiling is read once and acted on, so the arithmetic is pinned here."""
from decimal import Decimal

import pytest

from server import target_price


def variant(price='295', cost='192', pricing='FIXED'):
    return {'default_price': price, 'cost': cost, 'default_pricing_type': pricing}


SHOPEE = 'https://shopee.ph/Kuhne-Mustard-Dijon-185g-i.284922593.56757096831'


def test_the_margin_comes_off_the_sell_price_and_is_not_a_markup_on_cost():
    # The whole feature turns on this: 30% of 295 off the top is 206.50, while a
    # 30% markup would allow 226.92. The catalogue buys the first way.
    assert target_price.target(Decimal('295')) == Decimal('206.50')
    assert target_price.target(Decimal('295')) != (Decimal('295') / Decimal('1.3')).quantize(Decimal('0.01'))


def test_a_ceiling_is_rounded_down_so_it_never_gains_headroom():
    assert target_price.target(Decimal('10.01')) == Decimal('7.00')  # 7.007 exactly
    assert target_price.target(Decimal('0.99')) == Decimal('0.69')   # 0.693 exactly


def test_the_till_price_that_restores_the_margin_rounds_up_to_a_whole_peso():
    # Paying 167 needs 238.57 to hold 30%; 238 would leave the shop just short.
    assert target_price.implied_price(Decimal('167')) == Decimal('239')
    assert target_price.implied_price(Decimal('70')) == Decimal('100')


def test_a_price_that_already_fits_is_reported_as_fitting():
    row = target_price.for_buy_link(variant(price='249', cost='167'), None, SHOPEE)
    assert row['target_buy_price'] == '174.30'
    assert row['target_state'] == 'ok'
    assert row['implied_price'] is None


def test_a_price_above_the_ceiling_names_the_till_price_that_fixes_it():
    # The real catalogue row: Honey Ham priced at 24 while costing 167.
    row = target_price.for_buy_link(variant(price='24', cost='167'), None, SHOPEE)
    assert row['target_state'] == 'over'
    assert row['target_buy_price'] == '16.80'
    assert row['implied_price'] == '239'


def test_a_missing_cost_still_gets_a_ceiling_but_is_not_called_fitting():
    row = target_price.for_buy_link(variant(cost=None), None, SHOPEE)
    assert row['target_buy_price'] == '206.50'
    assert row['target_state'] == 'no_cost'
    assert row['recorded_cost'] is None


def test_a_cost_of_zero_is_not_read_as_a_free_unit():
    # Loyverse writes 0.00 where nobody recorded a cost. Calling that 'ok'
    # would claim the shop buys the item for nothing.
    row = target_price.for_buy_link(variant(cost='0'), None, SHOPEE)
    assert row['target_state'] == 'no_cost'
    assert row['recorded_cost'] is None


def test_an_unusable_cost_is_unknown_rather_than_zero():
    for bad in ('-5', 'NaN', 'about 200', ''):
        assert target_price.money(bad) is None


def test_a_store_of_its_own_price_overrides_the_default():
    store = {'settings_present': True, 'pricing_type': 'FIXED', 'price': '400'}
    row = target_price.for_buy_link(variant(), store, SHOPEE)
    assert row['sell_price'] == '400' and row['target_buy_price'] == '280.00'


def test_a_store_row_without_its_own_price_falls_back_to_the_default():
    store = {'settings_present': True, 'pricing_type': 'FIXED', 'price': None}
    assert target_price.for_buy_link(variant(), store, SHOPEE)['target_buy_price'] == '206.50'


def test_a_variable_priced_variant_has_no_ceiling_at_all():
    # The cashier types the price in per sale, so there is nothing to work from.
    row = target_price.for_buy_link(variant(pricing='VARIABLE'), None, SHOPEE)
    assert row['target_state'] == 'no_price' and row['target_buy_price'] is None


def test_an_item_with_no_price_shows_no_ceiling():
    row = target_price.for_buy_link(variant(price=None), None, SHOPEE)
    assert row['target_state'] == 'no_price' and row['target_buy_price'] is None


@pytest.mark.parametrize('url,inside', [
    (SHOPEE, True),
    ('https://shopee.ph/search?keyword=mustard', True),
    ('https://ph.shp.ee/qmXpKKrX', True),
    ('https://www.lazada.com.ph/products/x.html', False),
    ('https://shopee.ph.example.com/product/1/2', False),  # lookalike host
    ('https://notshopee.ph/product/1/2', False),
    (None, False),
    ('', False),
])
def test_only_a_link_that_really_points_at_shopee_gets_a_ceiling(url, inside):
    assert target_price.shopee(url) is inside


def test_a_supplier_we_do_not_pick_a_price_from_shows_nothing():
    row = target_price.for_buy_link(variant(), None, 'https://werdenberg.example/order')
    assert row['target_state'] == 'not_shopee'
    assert row['target_buy_price'] is None
    # Not even the sell price leaks out, so the view cannot half-render a ceiling.
    assert row['sell_price'] is None and row['target_margin'] is None


def test_the_margin_is_configurable_but_a_bare_thirty_is_refused(monkeypatch):
    monkeypatch.setenv('SH_TARGET_MARGIN', '0.35')
    assert target_price.margin() == Decimal('0.35')
    monkeypatch.setenv('SH_TARGET_MARGIN', '30')
    with pytest.raises(ValueError, match='above 0 and below 1'):
        target_price.margin()
    monkeypatch.setenv('SH_TARGET_MARGIN', 'a third')
    with pytest.raises(ValueError, match='decimal share'):
        target_price.margin()


def test_the_default_margin_is_thirty_percent_of_the_sell_price(monkeypatch):
    monkeypatch.delenv('SH_TARGET_MARGIN', raising=False)
    assert target_price.margin() == Decimal('0.30')


def test_the_ceiling_is_exact_and_never_a_float():
    row = target_price.for_buy_link(variant(price='0.10', cost=None), None, SHOPEE)
    # 0.10 * 0.70 is 0.07 exactly in decimal; in binary floats it is not.
    assert row['target_buy_price'] == '0.07'
