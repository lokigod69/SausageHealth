"""Synthetic catalogue cases only; live business data and credentials stay private.

The point of these tests is that an absent number stays absent. A missing stock
figure, an untracked item and an unset optimal stock must never reach the screen
as zero.
"""
from decimal import Decimal

import pytest

from server import loyverse
from server.db import connect
from test_app import env, client  # Shared fixture creates an isolated database per test.

STORE = 'store-a'
SECOND = 'store-b'
MONEY = {'code': 'PHP', 'decimal_places': 2}


def stores(*ids):
    return [{'id': store_id, 'name': 'Store ' + store_id[-1]} for store_id in ids]


def override(store_id=STORE, **fields):
    return {'store_id': store_id, 'pricing_type': 'FIXED', 'price': Decimal('250'),
            'available_for_sale': True, 'optimal_stock': None, 'low_stock': None, **fields}


def item(track_stock=True, variants=None, **fields):
    return {'id': 'item-1', 'item_name': 'Beef sausage', 'category_id': 'cat-1',
            'track_stock': track_stock, 'sold_by_weight': False, 'is_composite': False,
            'option1_name': 'Size', 'updated_at': '2026-09-10T02:00:00.000Z',
            'variants': variants if variants is not None else [variant()], **fields}


def variant(variant_id='variant-1', stores_list=None, **fields):
    return {'variant_id': variant_id, 'sku': '10023', 'barcode': '4800123456789',
            'option1_value': '500 g', 'cost': Decimal('120.50'), 'default_price': Decimal('250'),
            'default_pricing_type': 'FIXED', 'updated_at': '2026-09-10T02:00:00.000Z',
            'stores': stores_list if stores_list is not None else [override()], **fields}


def level(in_stock, variant_id='variant-1', store_id=STORE):
    return {'variant_id': variant_id, 'store_id': store_id, 'in_stock': in_stock,
            'updated_at': '2026-09-11T01:00:00.000Z'}


def build(items, inventory, store_ids=(STORE,), categories=None, mapping=None):
    return loyverse.build(list(stores(*store_ids)), categories if categories is not None else
                          [{'id': 'cat-1', 'name': 'Sausages'}], items, inventory, mapping or {}, MONEY)


def only(catalogue):
    return catalogue['items'][0]['variants'][0]['stores'][0]


def test_untracked_stock_is_reported_as_untracked_not_zero():
    # Loyverse zeroes inventory levels when tracking is off; that zero is not a count.
    row = only(build([item(track_stock=False)], [level(Decimal('0'))]))
    assert row['stock_state'] == 'not_tracked'
    assert row['in_stock'] is None
    assert row['below_optimal'] is None and row['low_stock_alert'] is False


def test_tracked_variant_without_an_inventory_level_is_unknown_not_zero():
    row = only(build([item()], []))
    assert row['stock_state'] == 'unknown' and row['in_stock'] is None


def test_a_real_zero_count_is_preserved_exactly():
    row = only(build([item()], [level(Decimal('0'))]))
    assert row['stock_state'] == 'tracked' and row['in_stock'] == '0'


def test_exact_decimals_survive_and_floats_are_refused():
    row = only(build([item(variants=[variant(stores_list=[override(price=Decimal('249.99'))])])],
                     [level(Decimal('7.250'))]))
    assert row['in_stock'] == '7.250' and row['price'] == '249.99'
    with pytest.raises(ValueError):
        build([item()], [level(7.25)])
    with pytest.raises(ValueError):
        build([item()], [level(Decimal('NaN'))])


def test_unset_optimal_and_low_stock_stay_unset():
    row = only(build([item()], [level(Decimal('4'))]))
    assert row['optimal_stock'] is None and row['low_stock'] is None
    assert row['below_optimal'] is None and row['low_stock_alert'] is False


def test_shortfall_is_only_computed_when_both_numbers_are_known():
    catalogue = build([item(variants=[variant(stores_list=[override(optimal_stock=Decimal('12'),
                                                                    low_stock=Decimal('4'))])])],
                      [level(Decimal('4.5'))])
    row = only(catalogue)
    assert row['optimal_stock'] == '12' and row['below_optimal'] == '7.5'
    assert row['low_stock_alert'] is False
    # The low-stock alert fires at the threshold, matching the Loyverse rule.
    at_threshold = only(build([item(variants=[variant(stores_list=[override(low_stock=Decimal('4'))])])],
                              [level(Decimal('4'))]))
    assert at_threshold['low_stock_alert'] is True
    # An unknown count cannot produce a shortfall, even with an optimal stock set.
    unknown = only(build([item(variants=[variant(stores_list=[override(optimal_stock=Decimal('12'))])])], []))
    assert unknown['stock_state'] == 'unknown' and unknown['below_optimal'] is None


def test_composite_items_without_production_report_components_not_own_stock():
    row = only(build([item(is_composite=True)], [level(Decimal('0'))]))
    assert row['stock_state'] == 'components_only' and row['in_stock'] is None
    produced = only(build([item(is_composite=True, use_production=True)], [level(Decimal('3'))]))
    assert produced['stock_state'] == 'tracked' and produced['in_stock'] == '3'


def test_a_store_with_no_settings_for_a_variant_is_marked_absent():
    catalogue = build([item()], [level(Decimal('2'))], store_ids=(STORE, SECOND))
    second = catalogue['items'][0]['variants'][0]['stores'][1]
    assert second['settings_present'] is False
    assert second['price'] is None and second['available_for_sale'] is None
    assert second['stock_state'] == 'unknown'


def test_duplicate_or_missing_identities_stop_the_capture():
    with pytest.raises(ValueError, match='Duplicate inventory level'):
        build([item()], [level(Decimal('1')), level(Decimal('2'))])
    with pytest.raises(ValueError, match='Duplicate Loyverse variant'):
        build([item(variants=[variant(), variant()])], [])
    with pytest.raises(ValueError, match='Duplicate Loyverse store'):
        build([item()], [], store_ids=(STORE, STORE))
    with pytest.raises(ValueError, match='Duplicate store settings'):
        build([item(variants=[variant(stores_list=[override(), override()])])], [])
    with pytest.raises(ValueError, match='no id'):
        build([dict(item(), id=None)], [])
    with pytest.raises(ValueError, match='missing its variant or store'):
        build([item()], [dict(level(Decimal('1')), variant_id=None)])


def test_deleted_items_and_variants_are_left_out():
    catalogue = build([dict(item(), deleted_at='2026-09-01T00:00:00.000Z'),
                       dict(item(), id='item-2', item_name='Kefir',
                            variants=[variant('variant-2'), dict(variant('variant-3'),
                                                                 deleted_at='2026-09-01T00:00:00.000Z')])], [])
    assert [row['id'] for row in catalogue['items']] == ['item-2']
    assert [v['variant_id'] for v in catalogue['items'][0]['variants']] == ['variant-2']


def test_unmapped_stores_are_never_attributed_to_a_workspace_store():
    catalogue = build([item()], [level(Decimal('1'))], store_ids=(STORE, SECOND),
                      mapping={STORE: 'sausage'})
    assert [store['workspace_store'] for store in catalogue['stores']] == ['sausage', None]
    assert catalogue['counts']['mapped_stores'] == 1
    # A configured id that this account does not return is surfaced, not silently ignored.
    absent = build([item()], [], mapping={'store-zzz': 'health'})
    assert absent['unmatched_store_mapping'] == ['store-zzz']


def test_store_map_configuration_is_validated(monkeypatch):
    monkeypatch.setenv('SH_LOYVERSE_STORE_MAP', '{"store-a": "sausage"}')
    assert loyverse.store_map() == {STORE: 'sausage'}
    monkeypatch.setenv('SH_LOYVERSE_STORE_MAP', '{"store-a": "warehouse"}')
    with pytest.raises(ValueError):
        loyverse.store_map()
    monkeypatch.setenv('SH_LOYVERSE_STORE_MAP', 'not json')
    with pytest.raises(ValueError):
        loyverse.store_map()
    monkeypatch.setenv('SH_LOYVERSE_STORE_MAP', '{"store-a": "sausage", "store-b": "sausage"}')
    with pytest.raises(ValueError, match='two Loyverse stores'):
        build([item()], [], store_ids=(STORE, SECOND), mapping=loyverse.store_map())


def test_counts_separate_known_from_unknown():
    catalogue = build([item(variants=[variant(stores_list=[override(optimal_stock=Decimal('10'))]),
                                      variant('variant-2', stores_list=[override(available_for_sale=False)])]),
                       dict(item(), id='item-2', item_name='Gift card', track_stock=False,
                            variants=[variant('variant-3')])],
                      [level(Decimal('2'))])
    assert catalogue['counts'] == {'stores': 1, 'mapped_stores': 0, 'items': 2, 'variants': 3,
                                   'variant_store_rows': 3, 'tracked': 1, 'not_tracked': 1,
                                   'components_only': 0, 'unknown_stock': 1, 'below_optimal': 1,
                                   'low_stock_alerts': 0, 'optimal_stock_set': 1, 'unavailable': 1}


def snapshot(store_ids=(STORE,), mapping=None):
    return build([item(variants=[variant(stores_list=[override(store_id=store_id)
                                                      for store_id in store_ids])])],
                 [level(Decimal('5'))], store_ids=store_ids, mapping=mapping)


def connect_loyverse(monkeypatch, catalogue=None, requests_made=5):
    monkeypatch.setenv('SH_LOYVERSE_ENABLED', '1')
    monkeypatch.setenv('SH_LOYVERSE_TOKEN', 'test-token-never-a-real-credential')
    monkeypatch.setenv('SH_LOYVERSE_COOLDOWN_SECONDS', '0')
    calls = []

    def capture():
        calls.append(True)
        return catalogue if catalogue is not None else snapshot(), requests_made
    monkeypatch.setattr(loyverse, 'capture', capture)
    return calls


def test_disconnected_workspace_never_calls_loyverse(env, monkeypatch):
    monkeypatch.delenv('SH_LOYVERSE_ENABLED', raising=False)
    monkeypatch.setattr(loyverse, 'capture', lambda: pytest.fail('Loyverse must not be called'))
    c = client()
    listing = c.get('/api/loyverse/items')
    assert listing.status_code == 200
    assert listing.json() == {'connection': 'not_connected', 'can_refresh': True,
                              'last_attempt': None, 'catalogue': None, 'captured_at': None}
    assert c.post('/api/loyverse/refresh').status_code == 503
    assert c.get('/api/system').json()['loyverse'] == 'not_connected'


def test_store_team_cannot_open_the_item_list(env, monkeypatch):
    connect_loyverse(monkeypatch)
    staff = client('staff@test.local')
    assert staff.get('/api/loyverse/items').status_code == 403
    assert staff.post('/api/loyverse/refresh').status_code == 403


def test_refresh_stores_a_snapshot_and_audits_the_read(env, monkeypatch):
    calls = connect_loyverse(monkeypatch)
    c = client()
    result = c.post('/api/loyverse/refresh')
    assert result.status_code == 200 and len(calls) == 1
    body = result.json()
    assert body['connection'] == 'ready'
    assert body['catalogue']['counts']['items'] == 1
    assert body['catalogue']['items'][0]['variants'][0]['stores'][0]['in_stock'] == '5'
    assert c.get('/api/loyverse/items').json()['captured_at'] == body['captured_at']
    actions = [row['action'] for row in c.get('/api/audit').json()]
    assert 'loyverse.refreshed' in actions and 'loyverse.refresh_requested' in actions


def test_the_credential_never_appears_in_a_response(env, monkeypatch):
    connect_loyverse(monkeypatch)
    c = client()
    c.post('/api/loyverse/refresh')
    for path in ('/api/loyverse/items', '/api/system', '/api/audit'):
        assert 'test-token-never-a-real-credential' not in c.get(path).text


def test_cooldown_and_daily_cap_bound_the_account_rate_limit(env, monkeypatch):
    calls = connect_loyverse(monkeypatch)
    monkeypatch.setenv('SH_LOYVERSE_COOLDOWN_SECONDS', '900')
    c = client()
    assert c.post('/api/loyverse/refresh').status_code == 200
    blocked = c.post('/api/loyverse/refresh')
    assert blocked.status_code == 429 and 'Wait' in blocked.json()['detail']
    monkeypatch.setenv('SH_LOYVERSE_COOLDOWN_SECONDS', '0')
    monkeypatch.setenv('SH_LOYVERSE_DAILY_SYNCS', '1')
    assert c.post('/api/loyverse/refresh').status_code == 429
    assert len(calls) == 1


def test_a_failed_read_keeps_the_previous_list_and_hides_provider_detail(env, monkeypatch):
    connect_loyverse(monkeypatch)
    c = client()
    assert c.post('/api/loyverse/refresh').status_code == 200
    first = c.get('/api/loyverse/items').json()['captured_at']

    def explode():
        raise RuntimeError('Bearer test-token-never-a-real-credential rejected by upstream')
    monkeypatch.setattr(loyverse, 'capture', explode)
    failure = c.post('/api/loyverse/refresh')
    assert failure.status_code == 502
    assert 'test-token-never-a-real-credential' not in failure.text
    current = c.get('/api/loyverse/items').json()
    assert current['captured_at'] == first and current['catalogue'] is not None
    assert current['last_attempt']['status'] == 'failed'
    assert 'test-token-never-a-real-credential' not in current['last_attempt']['error']


def test_a_store_operator_sees_only_their_mapped_store(env, monkeypatch):
    connect_loyverse(monkeypatch, catalogue=snapshot((STORE, SECOND), {STORE: 'sausage'}))
    owner = client()
    assert owner.post('/api/loyverse/refresh').status_code == 200
    owner_view = owner.get('/api/loyverse/items').json()['catalogue']
    assert [store['id'] for store in owner_view['stores']] == [STORE, SECOND]
    assert owner_view['unmatched_store_mapping'] == []
    manager = client('manager@test.local')
    manager_view = manager.get('/api/loyverse/items').json()['catalogue']
    assert [store['id'] for store in manager_view['stores']] == [STORE]
    assert [row['store_id'] for row in manager_view['items'][0]['variants'][0]['stores']] == [STORE]
    assert manager_view['counts']['stores'] == 1
    assert 'unmatched_store_mapping' not in manager_view


def test_an_operator_with_no_mapped_store_sees_an_empty_scope_not_another_store(env, monkeypatch):
    connect_loyverse(monkeypatch, catalogue=snapshot((STORE,), {STORE: 'health'}))
    assert client().post('/api/loyverse/refresh').status_code == 200
    manager = client('manager@test.local')  # assigned to sausage only
    view = manager.get('/api/loyverse/items').json()['catalogue']
    assert view['stores'] == [] and view['counts']['variant_store_rows'] == 0
    assert view['items'][0]['variants'][0]['stores'] == []


def test_only_the_newest_snapshots_keep_their_payload(env, monkeypatch):
    connect_loyverse(monkeypatch)
    c = client()
    for _ in range(loyverse.KEEP_PAYLOADS + 2):
        assert c.post('/api/loyverse/refresh').status_code == 200
    with connect() as db:
        stored = db.execute('SELECT COUNT(*) FROM loyverse_syncs WHERE payload IS NOT NULL').fetchone()[0]
        total = db.execute('SELECT COUNT(*) FROM loyverse_syncs').fetchone()[0]
    assert stored == loyverse.KEEP_PAYLOADS and total == loyverse.KEEP_PAYLOADS + 2


def test_scientific_notation_from_the_source_is_written_in_plain_digits():
    row = only(build([item()], [level(Decimal('1E+3'))]))
    assert row['in_stock'] == '1000'
    priced = only(build([item(variants=[variant(stores_list=[override(price=Decimal('2.5E+2'))])])],
                        [level(Decimal('1'))]))
    assert priced['price'] == '250'
