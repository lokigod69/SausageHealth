"""A buying link is typed by a person and ends up in an href, so what is refused matters."""
from datetime import date

import pytest

from server import item_links, suppliers
from server.db import connect
from test_app import env, client, HEADERS  # Shared fixture creates an isolated database per test.

SHOPEE = 'https://shopee.ph/Kuhne-Mustard-Dijon-185g-i.284922593.56757096831'
LAZADA = 'https://www.lazada.com.ph/products/mustard-i123.html'


def put(c, variant='v1', **body):
    return c.put(f'/api/item-links/{variant}', json=body)


def test_a_manager_records_a_link_without_touching_configuration(env):
    # The point of the feature: no hosting login, no deploy, no secret.
    manager = client('manager@test.local')
    saved = put(manager, url=SHOPEE, sku='10437', item_name='Mustard')
    assert saved.status_code == 200
    assert saved.json()['url'] == SHOPEE
    assert manager.get('/api/item-links').json()[0]['sku'] == '10437'


def test_the_owner_can_record_one_too(env):
    assert put(client(), url=SHOPEE).status_code == 200


def test_a_shop_floor_account_cannot_record_a_link(env):
    refused = put(client('staff@test.local'), url=SHOPEE)
    assert refused.status_code == 403


def test_only_plain_https_links_are_stored(env):
    owner = client()
    for bad in ('javascript:alert(1)', 'data:text/html,<script>', 'http://shopee.ph/x',
                'https://shopee.ph/"onmouseover="x', 'https://shopee.ph/a\nb'):
        refused = put(owner, url=bad)
        assert refused.status_code == 422, bad
    assert owner.get('/api/item-links').json() == []


def test_an_over_long_link_is_refused(env):
    assert put(client(), url='https://shopee.ph/' + 'a' * 700).status_code == 422


def test_either_slot_alone_is_enough_to_keep_a_record(env):
    owner = client()
    only_lazada = put(owner, lazada_url=LAZADA)
    assert only_lazada.json()['url'] is None
    assert only_lazada.json()['lazada_url'] == LAZADA
    only_shopee = put(owner, variant='v2', url=SHOPEE)
    assert only_shopee.json()['lazada_url'] is None
    assert only_shopee.json()['url'] == SHOPEE


def test_a_link_from_neither_marketplace_is_refused(env):
    # There is no third slot any more, so an unfiled link has nowhere to go and
    # is refused rather than filed under the wrong marketplace.
    owner = client()
    for field in ('url', 'lazada_url'):
        refused = put(owner, **{field: 'https://butcher.example/pork'})
        assert refused.status_code == 422, field
    assert owner.get('/api/item-links').json() == []


def test_a_lazada_page_in_the_shopee_slot_is_refused(env):
    # Mislabelling it would also silently deny it a buying ceiling.
    owner = client()
    refused = put(owner, url=LAZADA)
    assert refused.status_code == 422 and 'shopee.ph' in refused.json()['detail']
    assert put(owner, lazada_url=SHOPEE).status_code == 422


def test_a_link_from_anywhere_else_is_refused(env):
    assert put(client(), url='https://butcher.example/pork').status_code == 422


def test_a_shopee_lookalike_host_is_not_accepted_as_shopee(env):
    refused = put(client(), url='https://shopee.ph.example.com/product/1/2')
    assert refused.status_code == 422


def test_a_short_shopee_link_is_accepted_and_stored_as_pasted(env):
    short = 'https://ph.shp.ee/qmXpKKrX'
    assert put(client(), url=short).json()['url'] == short


def test_clearing_every_field_removes_the_record_rather_than_emptying_it(env):
    # An empty record and no record mean the same thing; keeping both lets them disagree.
    owner = client()
    put(owner, url=SHOPEE, lazada_url=LAZADA)
    cleared = put(owner, url=None, lazada_url=None, alternative_url=None)
    assert cleared.status_code == 200
    assert owner.get('/api/item-links').json() == []


def test_recording_twice_replaces_rather_than_duplicates(env):
    owner = client()
    put(owner, url=SHOPEE, lazada_url=LAZADA)
    put(owner, url='https://shopee.ph/other-i.9.9')
    rows = owner.get('/api/item-links').json()
    # The replacement is whole: the Lazada link from the first write is gone.
    assert len(rows) == 1
    assert rows[0]['url'] == 'https://shopee.ph/other-i.9.9'
    assert rows[0]['lazada_url'] is None


def test_removing_a_link_is_idempotent_and_says_which_it_was(env):
    owner = client()
    put(owner, url=SHOPEE)
    assert owner.delete('/api/item-links/v1').json()['already'] is False
    assert owner.delete('/api/item-links/v1').json()['already'] is True


def test_a_recorded_link_is_written_to_the_audit_trail(env):
    owner = client()
    put(owner, url=SHOPEE)
    owner.delete('/api/item-links/v1')
    actions = [row['action'] for row in owner.get('/api/audit').json()]
    assert 'item_link.recorded' in actions and 'item_link.removed' in actions


def test_the_links_are_readable_by_anyone_who_can_see_the_catalogue(env):
    put(client(), url=SHOPEE)
    assert client('staff@test.local').get('/api/item-links').status_code == 200


def test_signing_in_is_still_required(env):
    from fastapi.testclient import TestClient
    from server.main import app
    anonymous = TestClient(app, headers=HEADERS)
    assert anonymous.get('/api/item-links').status_code == 401
    assert anonymous.put('/api/item-links/v1', json={'url': SHOPEE}).status_code == 401


def test_whitespace_is_trimmed_so_a_pasted_link_still_works(env):
    saved = put(client(), url=f'  {SHOPEE}  ', note='  two   spaces  ')
    assert saved.json()['url'] == SHOPEE
    assert saved.json()['note'] == 'two spaces'


# ---------------------------------------------------------------- precedence
CONFIG = {
    'suppliers': [{'id': 'market', 'name': 'Marketplace', 'lead_days': 8,
                   'search_url': 'https://shopee.ph/search?keyword={query}'}],
    'rules': [{'match': {'category': 'Pantry'}, 'supplier': 'market'}],
    'links': {'10437': {'url': 'https://shopee.ph/configured-i.1.1'}},
}


def item():
    return {'name': 'Mustard', 'category_name': 'Pantry',
            'variants': [{'variant_id': 'v1', 'sku': '10437', 'default_price': '295',
                          'cost': '192', 'default_pricing_type': 'FIXED',
                          'stores': [{'store_id': 'store-a', 'stock_state': 'tracked',
                                      'in_stock': '1', 'sold_per_week': '2'}]}]}


def assigned(monkeypatch, stored=None):
    import json
    monkeypatch.setenv('SH_LOYVERSE_SUPPLIERS', json.dumps(CONFIG))
    result = suppliers.assign([item()], date(2026, 10, 5), suppliers.registry(), stored=stored)
    return result['assignments'][('v1', 'store-a')]


def test_a_link_the_shop_recorded_beats_one_in_configuration(monkeypatch):
    # Configuration needs a deploy, so it is the staler of the two by construction.
    entry = assigned(monkeypatch, {'v1': {'url': SHOPEE, 'lazada_url': None, 'note': None}})
    assert entry['buy_url'] == SHOPEE
    assert entry['buy_kind'] == 'listing'


def test_configuration_still_applies_where_the_shop_recorded_nothing(monkeypatch):
    assert assigned(monkeypatch)['buy_url'] == 'https://shopee.ph/configured-i.1.1'


def test_an_empty_recorded_row_does_not_shadow_configuration(monkeypatch):
    entry = assigned(monkeypatch, {'v1': {'url': None, 'lazada_url': None, 'note': None}})
    assert entry['buy_url'] == 'https://shopee.ph/configured-i.1.1'


def test_shopee_leads_and_lazada_follows_as_a_source(monkeypatch):
    entry = assigned(monkeypatch, {'v1': {'url': SHOPEE, 'lazada_url': LAZADA, 'note': None}})
    assert entry['buy_url'] == SHOPEE and entry['buy_kind'] == 'listing'
    assert {'name': 'Lazada', 'url': LAZADA, 'note': None} in entry['other_sources']


def test_without_a_shopee_page_lazada_becomes_the_one_to_open(monkeypatch):
    entry = assigned(monkeypatch, {'v1': {'url': None, 'lazada_url': LAZADA, 'note': None}})
    assert entry['buy_url'] == LAZADA and entry['buy_kind'] == 'listing'
    # And it earns no ceiling, because a Lazada price is not a Shopee price.
    assert entry['target_state'] == 'not_shopee'


def test_a_recorded_link_still_earns_the_buying_ceiling(monkeypatch):
    # The ceiling follows the link's host, so a recorded Shopee page qualifies.
    entry = assigned(monkeypatch, {'v1': {'url': SHOPEE, 'lazada_url': None, 'note': None}})
    assert entry['target_buy_price'] == '206.50' and entry['target_state'] == 'ok'


# ---------------------------------------------------------------- shipped links
def stored_catalogue(sku='10437', variant_id='v-mustard'):
    """A snapshot the way a sync leaves one, which is what resolves a SKU."""
    import json as encoder
    from server.db import connect, now
    payload = {'captured_at': now(), 'items': [
        {'id': 'i1', 'name': 'Original Dijon Mustard 185g',
         'variants': [{'variant_id': variant_id, 'sku': sku}]}]}
    with connect() as db:
        owner = db.execute("SELECT id FROM users WHERE role='owner'").fetchone()['id']
        db.execute("""INSERT INTO loyverse_syncs(id,actor_id,started_at,finished_at,status,
                      payload,error,request_count) VALUES (?,?,?,?,?,?,?,?)""",
                   ('s1', owner, now(), now(), 'complete', encoder.dumps(payload), None, 1))


def test_a_shipped_link_needs_no_database_row(env):
    # The point of shipping them: a deploy carries them, nobody types them in.
    stored_catalogue()
    rows = client().get('/api/item-links').json()
    mustard = [row for row in rows if row['sku'] == '10437']
    assert len(mustard) == 1
    assert 'shopee.ph' in mustard[0]['url']
    assert mustard[0]['updated_by'] == 'shipped'


def test_a_link_the_shop_records_beats_the_shipped_one(env):
    stored_catalogue()
    owner = client()
    owner.put('/api/item-links/v-mustard', json={'url': 'https://shopee.ph/theirs-i.1.2'})
    rows = {row['variant_id']: row for row in owner.get('/api/item-links').json()}
    assert rows['v-mustard']['url'] == 'https://shopee.ph/theirs-i.1.2'
    assert rows['v-mustard']['updated_by'] != 'shipped'


def test_a_shipped_link_for_an_unknown_sku_is_simply_absent(env):
    # Attaching it to the wrong variant would be worse than not showing it.
    stored_catalogue(sku='99999', variant_id='v-other')
    rows = client().get('/api/item-links').json()
    assert [row for row in rows if row['variant_id'] == 'v-other'] == []


def test_shipped_links_need_no_snapshot_to_be_safe(env):
    # Before the first sync there is nothing to resolve against, and that is fine.
    assert client().get('/api/item-links').json() == []
