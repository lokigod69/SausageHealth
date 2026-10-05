"""A tablet session never expires, so what it cannot do matters more than usual."""
import time

from fastapi.testclient import TestClient

from server import devices
from server.db import connect
from server.main import app
from test_app import env, client, HEADERS  # Shared fixture creates an isolated database per test.


def operator_id():
    with connect() as db:
        return db.execute("SELECT id FROM users WHERE email='manager@test.local'").fetchone()['id']


def owner_id():
    with connect() as db:
        return db.execute("SELECT id FROM users WHERE role='owner'").fetchone()['id']


def pair(c, name='Counter tablet', acts_as=None):
    return c.post('/api/devices', json={'name': name, 'acts_as': acts_as or operator_id()})


def test_a_paired_tablet_stays_signed_in_and_speaks_for_its_account(env):
    owner = client()
    started = pair(owner)
    assert started.status_code == 200
    code = started.json()['code']

    tablet = TestClient(app, headers=HEADERS)
    assert tablet.get('/api/me').status_code == 401
    assert tablet.post('/api/devices/redeem', json={'code': code}).status_code == 200
    me = tablet.get('/api/me')
    assert me.status_code == 200
    assert me.json()['role'] == 'manager' and me.json()['device'] == 'Counter tablet'
    # The cookie carries no expiry of its own that would sign the tablet out.
    assert 'sh_device' in tablet.cookies


def test_the_code_can_only_be_redeemed_once(env):
    owner = client()
    code = pair(owner).json()['code']
    first = TestClient(app, headers=HEADERS)
    assert first.post('/api/devices/redeem', json={'code': code}).status_code == 200
    second = TestClient(app, headers=HEADERS)
    assert second.post('/api/devices/redeem', json={'code': code}).status_code == 404


def test_spacing_and_case_do_not_matter_when_typing_the_code(env):
    owner = client()
    code = pair(owner).json()['code']
    typed = ' '.join([code[:5].lower(), code[5:]])
    tablet = TestClient(app, headers=HEADERS)
    assert tablet.post('/api/devices/redeem', json={'code': typed}).status_code == 200


def test_guesses_are_counted_so_a_code_cannot_be_hammered(env, monkeypatch):
    owner = client()
    started = pair(owner).json()
    code = started['code']
    wrong = TestClient(app, headers=HEADERS)
    # Wrong codes of the right shape are counted against the code they aim at.
    for _ in range(devices.MAX_ATTEMPTS):
        assert wrong.post('/api/devices/redeem',
                          json={'code': code[:-1] + ('A' if code[-1] != 'A' else 'B')}
                          ).status_code == 404
    with connect() as db:
        db.execute('UPDATE devices SET attempts=? WHERE id=?',
                   (devices.MAX_ATTEMPTS, started['id']))
    assert TestClient(app, headers=HEADERS).post(
        '/api/devices/redeem', json={'code': code}).status_code == 429


def test_an_expired_code_is_refused(env):
    owner = client()
    started = pair(owner).json()
    with connect() as db:
        db.execute('UPDATE devices SET pairing_expires=? WHERE id=?',
                   (time.time() - 1, started['id']))
    assert TestClient(app, headers=HEADERS).post(
        '/api/devices/redeem', json={'code': started['code']}).status_code == 409


def test_revoking_cuts_the_tablet_off_immediately(env):
    owner = client()
    started = pair(owner).json()
    tablet = TestClient(app, headers=HEADERS)
    tablet.post('/api/devices/redeem', json={'code': started['code']})
    assert tablet.get('/api/me').status_code == 200
    assert owner.post(f"/api/devices/{started['id']}/revoke").json()['ok'] is True
    # No waiting for an expiry: the next request is already refused.
    assert tablet.get('/api/me').status_code == 401
    assert owner.post(f"/api/devices/{started['id']}/revoke").json()['already'] is True


def test_a_tablet_cannot_be_paired_to_the_owner_account(env):
    owner = client()
    refused = pair(owner, acts_as=owner_id())
    assert refused.status_code == 422
    assert 'owner' in refused.json()['detail']


def test_a_tablet_inherits_only_its_account_s_reach(env):
    owner = client()
    started = pair(owner).json()
    tablet = TestClient(app, headers=HEADERS)
    tablet.post('/api/devices/redeem', json={'code': started['code']})
    # Paired to a store operator, so the owner-only surfaces stay closed.
    assert tablet.get('/api/export').status_code == 403
    assert tablet.get('/api/audit').status_code == 403
    assert tablet.get('/api/devices').status_code == 403
    assert tablet.post('/api/devices', json={'name': 'Another', 'acts_as': operator_id()}
                       ).status_code == 403
    # But the work it exists for is open.
    assert tablet.get('/api/entries').status_code == 200


def test_only_the_owner_pairs_lists_or_revokes(env):
    manager = client('manager@test.local')
    staff = client('staff@test.local')
    for c in (manager, staff):
        assert c.post('/api/devices', json={'name': 'Mine', 'acts_as': operator_id()}).status_code == 403
        assert c.get('/api/devices').status_code == 403
        assert c.post('/api/devices/anything/revoke').status_code == 403


def test_the_device_list_shows_what_the_owner_needs_to_decide(env):
    owner = client()
    started = pair(owner, name='Counter tablet').json()
    pending = owner.get('/api/devices').json()
    assert pending[0]['paired'] is False and pending[0]['revoked'] is False
    assert pending[0]['acts_as'] == 'manager'
    TestClient(app, headers=HEADERS).post('/api/devices/redeem', json={'code': started['code']})
    live = owner.get('/api/devices').json()
    assert live[0]['paired'] is True and live[0]['last_seen'] is not None
    owner.post(f"/api/devices/{started['id']}/revoke")
    assert owner.get('/api/devices').json()[0]['revoked'] is True


def test_signing_out_releases_a_tablet_being_handed_back(env):
    owner = client()
    started = pair(owner).json()
    tablet = TestClient(app, headers=HEADERS)
    tablet.post('/api/devices/redeem', json={'code': started['code']})
    assert tablet.post('/api/logout').status_code == 200
    assert tablet.get('/api/me').status_code == 401


def test_a_device_name_is_required_so_a_list_of_tablets_stays_readable(env):
    owner = client()
    assert pair(owner, name='x').status_code == 422
    assert owner.post('/api/devices', json={'name': 'Fine', 'acts_as': 'no-such-user'}
                      ).status_code == 422
