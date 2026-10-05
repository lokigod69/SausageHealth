"""Suppliers the shop records itself. No real supplier name appears in this repository."""
import json
from datetime import date

from server import shop_suppliers, suppliers
from server.db import connect
from test_app import env, client, HEADERS  # Shared fixture creates an isolated database per test.

# A configured registry that maps a whole category to a marketplace, which is
# exactly the kind of too-broad rule the shop needs to be able to correct.
CONFIGURED = {
    'suppliers': [{'id': 'market', 'name': 'Marketplace', 'lead_days': 8,
                   'search_url': 'https://shopee.ph/search?keyword={query}'}],
    'rules': [{'match': {'category': 'Breakfast'}, 'supplier': 'market'}],
}


def put(c, **body):
    return c.put('/api/shop-suppliers', json={'name': 'Dairy Farm', **body})


def dairy(**extra):
    return {'name': 'Dairy Farm', 'lead_min': 2, 'lead_max': 3,
            'whatsapp': '+63 900 000 0000', 'person': 'Ana',
            'match_names': 'Plain Yogurt\nKefir\nCoffee Beans', **extra}


def test_a_manager_records_a_supplier_with_its_number_and_its_products(env):
    manager = client('manager@test.local')
    saved = put(manager, **{k: v for k, v in dairy().items() if k != 'name'})
    assert saved.status_code == 200
    body = saved.json()
    assert body['id'] == 'dairy-farm'
    # Written however people write it, stored as digits for a wa.me link.
    assert body['whatsapp'] == '639000000000'
    assert body['match_names'] == 'Plain Yogurt\nKefir\nCoffee Beans'


def test_a_shop_floor_account_cannot_record_a_supplier(env):
    assert put(client('staff@test.local'), lead_min=2).status_code == 403


def test_the_shop_s_own_products_reach_the_supplier_it_recorded(env, monkeypatch):
    owner = client()
    put(owner, **{k: v for k, v in dairy().items() if k != 'name'})
    monkeypatch.setenv('SH_LOYVERSE_SUPPLIERS', json.dumps(CONFIGURED))
    registry = shop_suppliers.merged(suppliers.registry())
    rule = suppliers.match(registry['rules'], 'Plain Yogurt 500g', 'Dairy')
    assert rule and registry['suppliers'][rule['supplier']]['name'] == 'Dairy Farm'
    assert registry['suppliers']['dairy-farm']['contact']['whatsapp'] == '639000000000'
    # The configured supplier is still there; nothing was replaced.
    assert 'market' in registry['suppliers']


def test_a_recorded_rule_corrects_a_configured_one_that_was_too_broad(env, monkeypatch):
    # The configured rule sweeps the whole Breakfast category to the marketplace.
    owner = client()
    put(owner, lead_min=2, match_names='Walnut Granola')
    monkeypatch.setenv('SH_LOYVERSE_SUPPLIERS', json.dumps(CONFIGURED))
    registry = shop_suppliers.merged(suppliers.registry())
    granola = suppliers.match(registry['rules'], 'Walnut Granola 200g', 'Breakfast')
    assert granola['supplier'] == 'dairy-farm'
    # Everything else in that category still goes where configuration says.
    other = suppliers.match(registry['rules'], 'Corn Flakes 400g', 'Breakfast')
    assert other['supplier'] == 'market'


def test_the_shop_can_work_with_no_configuration_at_all(env, monkeypatch):
    monkeypatch.delenv('SH_LOYVERSE_SUPPLIERS', raising=False)
    assert suppliers.registry() is None
    put(client(), **{k: v for k, v in dairy().items() if k != 'name'})
    registry = shop_suppliers.merged(suppliers.registry())
    assert registry and 'dairy-farm' in registry['suppliers']


def test_a_recorded_supplier_reaches_the_reorder_plan(env, monkeypatch):
    put(client(), **{k: v for k, v in dairy().items() if k != 'name'})
    monkeypatch.delenv('SH_LOYVERSE_SUPPLIERS', raising=False)
    item = {'name': 'Plain Yogurt 500g', 'category_name': 'Dairy',
            'variants': [{'variant_id': 'v1', 'sku': '1', 'stores': [
                {'store_id': 'store-a', 'stock_state': 'tracked',
                 'in_stock': '1', 'sold_per_week': '7'}]}]}
    result = suppliers.assign([item], date(2026, 10, 5), shop_suppliers.merged(None))
    entry = result['assignments'][('v1', 'store-a')]
    assert entry['supplier_name'] == 'Dairy Farm'
    assert entry['contact']['whatsapp'] == '639000000000'
    assert entry['contact']['person'] == 'Ana'
    assert entry['lead_days'] == {'min': 2, 'max': 3}


def test_either_a_lead_time_or_a_weekday_cycle_is_required(env):
    owner = client()
    assert put(owner).status_code == 422
    assert put(owner, lead_min=2).status_code == 200
    assert put(owner, order_weekday='thursday', delivery_weekday='friday').status_code == 200


def test_half_a_cycle_is_refused(env):
    refused = put(client(), order_weekday='thursday')
    assert refused.status_code == 422
    assert 'delivery day' in refused.json()['detail']


def test_a_single_lead_day_fills_both_ends(env):
    saved = put(client(), lead_max=4).json()
    assert saved['lead_min'] == 4 and saved['lead_max'] == 4


def test_a_number_that_is_not_a_number_is_refused(env):
    refused = put(client(), lead_min=2, whatsapp='call the shop')
    assert refused.status_code == 422


def test_a_weekday_that_is_not_a_weekday_is_refused(env):
    refused = put(client(), order_weekday='someday', delivery_weekday='friday')
    assert refused.status_code == 422


def test_the_id_comes_from_the_name_so_nobody_has_to_invent_one(env):
    saved = client().put('/api/shop-suppliers',
                         json={'name': '  León & Sons (Bohol)  ', 'lead_min': 1}).json()
    assert saved['id'] == 'leo-n-sons-bohol'


def test_recording_the_same_supplier_twice_replaces_it(env):
    owner = client()
    put(owner, lead_min=2, match_names='Kefir')
    put(owner, lead_min=5, match_names='Kefir\nPlain Yogurt')
    rows = owner.get('/api/shop-suppliers').json()
    assert len(rows) == 1 and rows[0]['lead_min'] == 5


def test_blank_and_duplicate_match_lines_are_dropped(env):
    saved = put(client(), lead_min=2,
                match_names='Kefir\n\n  Kefir  \n\nPlain Yogurt\n').json()
    assert saved['match_names'] == 'Kefir\nPlain Yogurt'


def test_removing_a_supplier_is_idempotent(env):
    owner = client()
    put(owner, lead_min=2)
    assert owner.delete('/api/shop-suppliers/dairy-farm').json()['already'] is False
    assert owner.delete('/api/shop-suppliers/dairy-farm').json()['already'] is True


def test_recording_and_removing_are_written_to_the_audit_trail(env):
    owner = client()
    put(owner, lead_min=2)
    owner.delete('/api/shop-suppliers/dairy-farm')
    actions = [row['action'] for row in owner.get('/api/audit').json()]
    assert 'supplier.recorded' in actions and 'supplier.removed' in actions


def test_the_list_is_readable_by_anyone_who_can_see_the_catalogue(env):
    put(client(), lead_min=2)
    assert client('staff@test.local').get('/api/shop-suppliers').status_code == 200


def test_signing_in_is_still_required(env):
    from fastapi.testclient import TestClient
    from server.main import app
    anonymous = TestClient(app, headers=HEADERS)
    assert anonymous.get('/api/shop-suppliers').status_code == 401


def test_a_recorded_supplier_can_replace_a_configured_one_by_reusing_its_id(env, monkeypatch):
    # The shop corrects a configured lead time without a deploy.
    client().put('/api/shop-suppliers',
                 json={'name': 'Marketplace', 'id': 'market', 'lead_min': 14})
    monkeypatch.setenv('SH_LOYVERSE_SUPPLIERS', json.dumps(CONFIGURED))
    registry = shop_suppliers.merged(suppliers.registry())
    assert registry['suppliers']['market']['lead_days'] == {'min': 14, 'max': 14}


def test_no_records_leaves_the_configured_registry_exactly_as_it_was(env, monkeypatch):
    monkeypatch.setenv('SH_LOYVERSE_SUPPLIERS', json.dumps(CONFIGURED))
    assert shop_suppliers.merged(suppliers.registry()) == suppliers.registry()
