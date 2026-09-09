import hashlib
import json
import sqlite3
import zipfile
import os
import secrets

import pytest
from fastapi.testclient import TestClient

from server.db import add_user, connect, data_dir, initialize, reset_password
from server.main import app
from server.manage import backup

HEADERS = {'origin': 'http://127.0.0.1:5180', 'x-sh-request': '1'}
PASSWORD = 'test-only-password-7294'


@pytest.fixture(params=['sqlite', 'postgres'])
def env(tmp_path, monkeypatch, request):
    monkeypatch.delenv('SH_DATABASE_URL', raising=False)
    monkeypatch.delenv('SH_DATABASE_BACKEND', raising=False)
    monkeypatch.delenv('VERCEL', raising=False)
    monkeypatch.delenv('SH_STORAGE', raising=False)
    schema = None
    if request.param == 'postgres':
        url = os.environ.get('SH_TEST_DATABASE_URL')
        if not url:
            pytest.skip('SH_TEST_DATABASE_URL is not configured.')
        import psycopg
        from psycopg import sql
        schema = 'sh_test_' + secrets.token_hex(8)
        with psycopg.connect(url) as db:
            db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
        monkeypatch.setenv('SH_DATABASE_URL', url)
        monkeypatch.setenv('SH_DATABASE_SCHEMA', schema)
    monkeypatch.setenv('SH_DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setenv('SH_ENV', 'test')
    monkeypatch.setenv('SH_ORIGIN', HEADERS['origin'])
    initialize()
    for email, role, stores in [('owner@test.local', 'owner', ['sausage', 'health']),
                                 ('manager@test.local', 'manager', ['sausage']),
                                 ('staff@test.local', 'staff', ['sausage']),
                                 ('other@test.local', 'staff', ['sausage'])]:
        add_user(email, email.split('@')[0], role, stores, PASSWORD)
    try:
        yield tmp_path
    finally:
        if schema:
            with psycopg.connect(url) as db:
                db.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def client(email='owner@test.local'):
    c = TestClient(app, headers=HEADERS)
    assert c.post('/api/login', json={'email': email, 'password': PASSWORD}).status_code == 200
    return c


def submit(c, key='11111111-2222-3333-4444', **overrides):
    data = dict(store='sausage', category='sales', title='Source for Tuesday', notes='Sales reported: PHP 1000. Not verified.', occurred_on='2026-09-08', request_key=key)
    data.update(overrides)
    return c.post('/api/entries', data=data)


def test_auth_cookie_csrf_logout_and_private_routes(env):
    c = TestClient(app, headers=HEADERS)
    assert c.get('/api/entries').status_code == 401
    assert c.get('/api/export').status_code == 401
    assert c.get('/api/system').status_code == 401
    denied = c.post('/api/login', json={'email': 'owner@test.local', 'password': PASSWORD}, headers={'origin': 'https://untrusted.example'})
    assert denied.status_code == 403
    login = c.post('/api/login', json={'email': 'owner@test.local', 'password': PASSWORD})
    assert login.status_code == 200
    assert 'HttpOnly' in login.headers['set-cookie'] and 'SameSite=strict' in login.headers['set-cookie']
    assert c.get('/api/me').json()['role'] == 'owner'
    assert c.post('/api/logout').status_code == 200
    assert c.get('/api/me').status_code == 401


def test_login_rate_limit_is_persisted(env):
    c = TestClient(app, headers=HEADERS)
    for _ in range(10):
        assert c.post('/api/login', json={'email': 'nobody@test.local', 'password': PASSWORD}).status_code == 401
    assert c.post('/api/login', json={'email': 'nobody@test.local', 'password': PASSWORD}).status_code == 429


def test_notes_survive_new_client_and_retry_is_idempotent(env):
    c = client()
    first = submit(c)
    assert first.status_code == 201, first.text
    assert submit(c).json()['id'] == first.json()['id']
    assert len(client().get('/api/entries').json()) == 1
    assert first.json()['status'] == 'needs_review'
    assert first.json()['notes'] == 'Sales reported: PHP 1000. Not verified.'
    assert 'request_key' not in first.json()


def test_role_and_store_scope_cover_list_review_download_and_export(env):
    staff = client('staff@test.local')
    other = client('other@test.local')
    owner = client()
    manager = client('manager@test.local')
    own = submit(staff).json()
    submit(other, '22222222-2222-3333-4444')
    health = submit(owner, '33333333-2222-3333-4444', store='health').json()
    assert len(staff.get('/api/entries').json()) == 1
    assert len(manager.get('/api/entries').json()) == 2
    assert len(owner.get('/api/entries').json()) == 3
    assert submit(staff, '44444444-2222-3333-4444', store='health').status_code == 403
    assert submit(staff, '55555555-2222-3333-4444', store='both').status_code == 403
    assert staff.post(f"/api/entries/{own['id']}/review", json={'status': 'reviewed', 'version': 1}).status_code == 403
    assert manager.post(f"/api/entries/{health['id']}/review", json={'status': 'reviewed', 'version': 1}).status_code == 404
    assert manager.get('/api/export').status_code == 403
    assert staff.get('/api/audit').status_code == 403


def test_attachment_original_filename_checksum_and_download_authorization(env):
    staff = client('staff@test.local')
    raw = b'Original receipt: 3 packs; PHP 1500\r\n'
    response = staff.post('/api/entries', data={'store': 'sausage', 'category': 'suppliers', 'title': 'Receipt', 'occurred_on': '2026-09-08', 'request_key': '66666666-2222-3333-4444'}, files={'files': ('../../receipt.txt', raw, 'text/plain')})
    assert response.status_code == 201, response.text
    file = response.json()['attachments'][0]
    assert file['name'] == 'receipt.txt'
    assert file['sha256'] == hashlib.sha256(raw).hexdigest()
    assert staff.get('/api/files/' + file['id']).content == raw
    assert client('other@test.local').get('/api/files/' + file['id']).status_code == 404
    assert client('manager@test.local').get('/api/files/' + file['id']).content == raw
    assert staff.get('/api/files/' + file['id']).headers['content-type'] == 'application/octet-stream'


@pytest.mark.parametrize('overrides', [dict(notes=''), dict(title=' '), dict(category='invalid'), dict(occurred_on='not-a-date'), dict(request_key='bad')])
def test_invalid_records_are_rejected(env, overrides):
    assert submit(client(), **overrides).status_code == 422
    with connect() as db:
        assert db.execute('SELECT COUNT(*) FROM entries').fetchone()[0] == 0


def test_file_failure_rolls_back_files_and_record(env):
    c = client()
    response = c.post('/api/entries', data={'store': 'sausage', 'category': 'other', 'title': 'Bad upload', 'occurred_on': '2026-09-08', 'request_key': '77777777-2222-3333-4444'}, files=[('files', ('fine.txt', b'valid', 'text/plain')), ('files', ('unsafe.html', b'<script/>', 'text/html'))])
    assert response.status_code == 422
    assert list((data_dir() / 'uploads').iterdir()) == []
    assert c.get('/api/entries').json() == []


def test_review_is_versioned_and_audited(env):
    c = client()
    entry = submit(c).json()
    reviewed = c.post(f"/api/entries/{entry['id']}/review", json={'status': 'reviewed', 'note': 'Source readable.', 'version': 1})
    assert reviewed.status_code == 200
    assert reviewed.json()['version'] == 2
    assert reviewed.json()['notes'] == entry['notes']
    assert reviewed.json()['reviewer_name'] == 'owner'
    assert c.post(f"/api/entries/{entry['id']}/review", json={'status': 'needs_review', 'version': 1}).status_code == 409
    actions = [a['action'] for a in c.get('/api/audit').json()]
    assert 'entry.reviewed' in actions and 'entry.created' in actions


def test_backup_restore_originals_and_private_export(env, monkeypatch):
    if os.environ.get('SH_DATABASE_URL'):
        pytest.skip('Cloud backup/restore is covered by test_cloud.py.')
    c = client()
    row = c.post('/api/entries', data={'store': 'health', 'category': 'suppliers', 'title': 'Test only receipt', 'occurred_on': '2026-09-08', 'request_key': '88888888-2222-3333-4444'}, files={'files': ('receipt.txt', b'unchanged original', 'text/plain')}).json()
    path = backup(env / 'backup.zip')
    restored = env / 'restored'
    with zipfile.ZipFile(path) as archive:
        assert json.loads(archive.read('manifest.json'))['attachment_count'] == 1
        archive.extractall(restored)  # This is the test's own archive, not an untrusted input.
    with sqlite3.connect(restored / 'sausagehealth.sqlite') as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute('SELECT title FROM entries').fetchone()[0] == 'Test only receipt'
    assert (restored / 'uploads' / row['attachments'][0]['id']).read_bytes() == b'unchanged original'
    exported = c.get('/api/export').json()
    assert exported['schema_version'] == 1
    assert len(exported['entries']) == 1
    assert 'password' not in json.dumps(exported)
    monkeypatch.setenv('SH_DATA_DIR', str(restored))
    assert len(client().get('/api/entries').json()) == 1


def test_upload_size_gate_and_missing_api(env):
    c = client()
    assert c.post('/api/entries', content=b'x', headers={'content-length': str(110 * 1024 * 1024)}).status_code == 413
    assert c.get('/api/missing').status_code == 404
    assert c.get('/api/system').json()['ai'] == 'not_connected'
    assert c.get('/api/entries').headers['cache-control'] == 'no-store'


def test_reset_revokes_sessions_and_old_password(env):
    c = client()
    reset_password('owner@test.local', 'a-new-test-only-password')
    assert c.get('/api/me').status_code == 401
    assert c.post('/api/login', json={'email': 'owner@test.local', 'password': PASSWORD}).status_code == 401
    assert c.post('/api/login', json={'email': 'owner@test.local', 'password': 'a-new-test-only-password'}).status_code == 200
