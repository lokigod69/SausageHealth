"""A supplier picked by hand for one product. Synthetic names only."""
import json
from datetime import date

from server import item_suppliers, suppliers
from test_app import env, client, HEADERS  # Shared fixture creates an isolated database per test.

CONFIG = {
    'suppliers': [
        {'id': 'market', 'name': 'Marketplace', 'lead_days': 8},
        {'id': 'dairy', 'name': 'Dairy Farm', 'lead_days': 1},
    ],
    # A broad rule, which is exactly what a hand-picked choice has to be able to beat.
    'rules': [{'match': {'category': 'Breakfast'}, 'supplier': 'market'}],
}


def item(variant_id='v1', name='Walnut Granola 200g', category='Breakfast'):
    return {'name': name, 'category_name': category,
            'variants': [{'variant_id': variant_id, 'sku': '1', 'stores': [
                {'store_id': 'store-a', 'stock_state': 'tracked',
                 'in_stock': '2', 'sold_per_week': '7'}]}]}


def plan(monkeypatch, chosen=None, items=None):
    monkeypatch.setenv('SH_LOYVERSE_SUPPLIERS', json.dumps(CONFIG))
    return suppliers.assign(items or [item()], date(2026, 10, 5),
                            suppliers.registry(), chosen=chosen)


def test_a_choice_beats_a_rule(env, monkeypatch):
    entry = plan(monkeypatch, {'v1': 'dairy'})['assignments'][('v1', 'store-a')]
    assert entry['supplier_name'] == 'Dairy Farm'
    assert entry['by_hand'] is True
    assert entry['lead_days'] == {'min': 1, 'max': 1}


def test_without_a_choice_the_rule_still_decides(env, monkeypatch):
    entry = plan(monkeypatch)['assignments'][('v1', 'store-a')]
    assert entry['supplier_name'] == 'Marketplace'
    assert entry['by_hand'] is False


def test_a_choice_naming_a_supplier_that_no_longer_exists_falls_back_to_the_rule(env, monkeypatch):
    # Dropping the product out of ordering entirely would be worse than the rule.
    entry = plan(monkeypatch, {'v1': 'deleted-supplier'})['assignments'][('v1', 'store-a')]
    assert entry['supplier_name'] == 'Marketplace'
    assert entry['by_hand'] is False


def test_a_choice_can_assign_a_product_no_rule_matched(env, monkeypatch):
    loose = item(name='Dark Chocolate Pistachio Kunafa', category=None)
    result = plan(monkeypatch, {'v1': 'dairy'}, [loose])
    assert result['assignments'][('v1', 'store-a')]['supplier_name'] == 'Dairy Farm'
    assert result['unassigned_count'] == 0


def test_a_choice_is_per_variant_not_per_item(env, monkeypatch):
    two = {'name': 'Muesli 350g', 'category_name': 'Breakfast', 'variants': [
        {'variant_id': 'v1', 'sku': '1', 'stores': [
            {'store_id': 'store-a', 'stock_state': 'tracked', 'in_stock': '1',
             'sold_per_week': '7'}]},
        {'variant_id': 'v2', 'sku': '2', 'stores': [
            {'store_id': 'store-a', 'stock_state': 'tracked', 'in_stock': '1',
             'sold_per_week': '7'}]}]}
    result = plan(monkeypatch, {'v2': 'dairy'}, [two])
    assert result['assignments'][('v1', 'store-a')]['supplier_name'] == 'Marketplace'
    assert result['assignments'][('v2', 'store-a')]['supplier_name'] == 'Dairy Farm'


# ---------------------------------------------------------------- the endpoint
def test_a_manager_assigns_one_product(env):
    manager = client('manager@test.local')
    saved = manager.put('/api/item-suppliers',
                        json={'variant_ids': ['v1'], 'supplier_id': 'dairy'})
    assert saved.status_code == 200 and saved.json()['count'] == 1
    assert item_suppliers.listing() == {'v1': 'dairy'}


def test_many_products_are_assigned_in_one_action(env):
    owner = client()
    result = owner.put('/api/item-suppliers',
                       json={'variant_ids': ['v1', 'v2', 'v3'], 'supplier_id': 'dairy'})
    assert result.json()['count'] == 3
    assert item_suppliers.listing() == {'v1': 'dairy', 'v2': 'dairy', 'v3': 'dairy'}


def test_an_empty_supplier_clears_the_choice_and_returns_to_the_rule(env):
    owner = client()
    owner.put('/api/item-suppliers', json={'variant_ids': ['v1'], 'supplier_id': 'dairy'})
    owner.put('/api/item-suppliers', json={'variant_ids': ['v1'], 'supplier_id': None})
    assert item_suppliers.listing() == {}


def test_reassigning_replaces_rather_than_duplicates(env):
    owner = client()
    owner.put('/api/item-suppliers', json={'variant_ids': ['v1'], 'supplier_id': 'dairy'})
    owner.put('/api/item-suppliers', json={'variant_ids': ['v1'], 'supplier_id': 'market'})
    assert item_suppliers.listing() == {'v1': 'market'}


def test_a_shop_floor_account_cannot_assign(env):
    refused = client('staff@test.local').put(
        '/api/item-suppliers', json={'variant_ids': ['v1'], 'supplier_id': 'dairy'})
    assert refused.status_code == 403


def test_no_products_is_refused(env):
    assert client().put('/api/item-suppliers',
                        json={'variant_ids': [], 'supplier_id': 'dairy'}).status_code == 422


def test_more_than_one_screen_at_a_time_is_refused(env):
    many = [f'v{index}' for index in range(item_suppliers.MAX_AT_ONCE + 1)]
    assert client().put('/api/item-suppliers',
                        json={'variant_ids': many, 'supplier_id': 'dairy'}).status_code == 422


def test_a_bulk_assignment_is_one_audit_line_not_hundreds(env):
    owner = client()
    owner.put('/api/item-suppliers',
              json={'variant_ids': ['v1', 'v2', 'v3'], 'supplier_id': 'dairy'})
    lines = [row for row in owner.get('/api/audit').json()
             if row['action'] == 'item_supplier.chosen']
    assert len(lines) == 1 and '3 product(s)' in lines[0]['detail']


def test_clearing_is_recorded_as_clearing(env):
    owner = client()
    owner.put('/api/item-suppliers', json={'variant_ids': ['v1'], 'supplier_id': None})
    actions = [row['action'] for row in owner.get('/api/audit').json()]
    assert 'item_supplier.cleared' in actions


def test_the_choices_are_readable_by_anyone_who_can_see_the_catalogue(env):
    client().put('/api/item-suppliers', json={'variant_ids': ['v1'], 'supplier_id': 'dairy'})
    assert client('staff@test.local').get('/api/item-suppliers').status_code == 200


def test_signing_in_is_still_required(env):
    from fastapi.testclient import TestClient
    from server.main import app
    anonymous = TestClient(app, headers=HEADERS)
    assert anonymous.get('/api/item-suppliers').status_code == 401
