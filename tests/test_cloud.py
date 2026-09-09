import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from test_app import env, client, HEADERS
from server import storage
from server.db import connect
from server.main import app


@pytest.fixture
def cloud(env, monkeypatch):
    monkeypatch.setenv('SH_STORAGE', 'blob')
    monkeypatch.setenv('SH_STORAGE_SIGNING_KEY', 'test-only-' + '7' * 48)
    contents = {}
    def read(file_id, size=None):
        raw = contents[file_id]
        if size is not None and len(raw) != size:
            raise ValueError('Wrong size')
        return raw
    monkeypatch.setattr(storage, 'read_original', read)
    return contents


def body(key='abcdefgh-1234-5678-9012', raw=b'original\r\n', **changes):
    result = {'request_key': key, 'store': 'sausage', 'category': 'other', 'title': 'Synthetic original',
              'notes': 'Test only', 'occurred_on': '2026-09-09',
              'files': [{'name': 'receipt.txt', 'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}]}
    result.update(changes)
    return result


def test_private_reservation_permissions_and_payload_retry(cloud):
    staff, other, owner = client('staff@test.local'), client('other@test.local'), client()
    assert TestClient(app, headers=HEADERS).post('/api/upload-intents', json=body()).status_code == 401
    assert staff.post('/api/upload-intents', json=body(store='health')).status_code == 403
    response = staff.post('/api/upload-intents', json=body())
    assert response.status_code == 200, response.text
    intent = response.json()
    assert staff.post('/api/upload-intents', json=body()).json()['id'] == intent['id']
    assert staff.post('/api/upload-intents', json=body(notes='changed')).status_code == 409
    assert other.post('/api/upload-intents', json=body()).status_code == 409
    endpoint = '/api/upload-intents/' + intent['id'] + '/finalize'
    assert other.post(endpoint).status_code == 404
    assert owner.post(endpoint).status_code == 404
    assert staff.post(endpoint).status_code == 503
    cloud[intent['files'][0]['id']] = b'original\r\n'
    saved = staff.post(endpoint)
    assert saved.status_code == 201, saved.text
    assert staff.post(endpoint).json()['id'] == saved.json()['id']
    assert staff.post('/api/upload-intents', json=body()).json()['entry']['id'] == saved.json()['id']
    assert len(staff.get('/api/entries').json()) == 1
    file_id = saved.json()['attachments'][0]['id']
    assert other.get('/api/files/' + file_id, follow_redirects=False).status_code == 404
    download = staff.get('/api/files/' + file_id, follow_redirects=False)
    assert download.status_code == 303 and download.headers['location'].startswith('/api/storage?grant=')
    assert 'no-store' in download.headers['cache-control']


def test_finalize_checksum_expiry_quota_and_notes(cloud, monkeypatch):
    c = client()
    intent = c.post('/api/upload-intents', json=body()).json()
    cloud[intent['files'][0]['id']] = b'wrongbytes'
    assert c.post('/api/upload-intents/' + intent['id'] + '/finalize').status_code == 503
    assert c.get('/api/entries').json() == []
    with connect() as db:
        db.execute('UPDATE upload_intents SET expires=? WHERE id=?', (time.time() - 1, intent['id']))
    assert c.post('/api/upload-intents', json=body()).status_code == 409
    assert c.post('/api/upload-intents/' + intent['id'] + '/finalize').status_code == 409
    monkeypatch.setenv('SH_STORAGE_MAX_BYTES', '1')
    assert c.post('/api/upload-intents', json=body(key='new-key-111111111111')).status_code == 429
    monkeypatch.setenv('SH_STORAGE_MAX_BYTES', '1000')
    note = c.post('/api/upload-intents', json=body(key='note-key-11111111111', files=[])).json()
    assert c.post('/api/upload-intents/' + note['id'] + '/finalize').status_code == 201


def test_concurrent_reservation_finalize_and_review(cloud):
    clients = [client(), client()]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda c: c.post('/api/upload-intents', json=body()), clients))
    assert all(r.status_code == 200 for r in responses), [r.text for r in responses]
    intent = responses[0].json()
    assert responses[1].json()['id'] == intent['id']
    cloud[intent['files'][0]['id']] = b'original\r\n'
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda c: c.post('/api/upload-intents/' + intent['id'] + '/finalize'), clients))
    assert all(r.status_code == 201 for r in responses), [r.text for r in responses]
    entry = responses[0].json()
    assert responses[1].json()['id'] == entry['id']
    with ThreadPoolExecutor(max_workers=2) as pool:
        reviews = list(pool.map(lambda c: c.post('/api/entries/' + entry['id'] + '/review',
                                                json={'status': 'reviewed', 'version': 1}), clients))
    assert sorted(r.status_code for r in reviews) == [200, 409]
    with connect() as db:
        assert db.execute('SELECT COUNT(*) FROM entries').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM attachments').fetchone()[0] == 1


def test_storage_grant_is_bounded(cloud):
    import base64
    token = storage.grant('a' * 32, 'put', 10, time.time() + 36000)
    encoded, signature = token.split('.')
    payload = json.loads(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)))
    assert payload['expires'] <= time.time() + 300
    assert payload['pathname'] == 'pilot/originals/' + 'a' * 32
    assert len(signature) == 64


def test_encrypted_cloud_backup_restore_and_session_revocation(cloud, monkeypatch, tmp_path):
    import os
    import secrets
    import psycopg
    from psycopg import sql
    from cryptography.exceptions import InvalidTag
    from server.cloud_backup import backup, restore
    if not os.environ.get('SH_DATABASE_URL'):
        pytest.skip('Cloud backup uses Postgres.')
    c = client()
    intent = c.post('/api/upload-intents', json=body()).json()
    cloud[intent['files'][0]['id']] = b'original\r\n'
    saved = c.post('/api/upload-intents/' + intent['id'] + '/finalize').json()
    key = tmp_path / 'key'
    key.write_text(secrets.token_hex(32))
    archive = tmp_path / 'backup.shb'
    result = backup(archive, key)
    assert result['attachment_count'] == 1
    assert b'Test only' not in archive.read_bytes()
    with pytest.raises(ValueError):
        backup(archive, key)
    with pytest.raises(ValueError):
        restore(archive, key)
    tampered = tmp_path / 'tampered.shb'
    raw = bytearray(archive.read_bytes())
    raw[-1] ^= 1
    tampered.write_bytes(raw)
    with pytest.raises(InvalidTag):
        restore(tampered, key)
    target = 'sh_test_restore_' + secrets.token_hex(8)
    url = os.environ['SH_DATABASE_URL']
    with psycopg.connect(url) as db:
        db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(target)))
    try:
        monkeypatch.setenv('SH_DATABASE_SCHEMA', target)
        monkeypatch.setenv('SH_BLOB_PREFIX', 'restore-test')
        restored_files = {}
        monkeypatch.setattr(storage, 'write_original', lambda file_id, raw: restored_files.__setitem__(file_id, raw))
        monkeypatch.setattr(storage, 'read_original', lambda file_id, size=None: restored_files[file_id])
        assert restore(archive, key)['sessions_restored'] == 0
        assert c.get('/api/me').status_code == 401
        records = client().get('/api/entries').json()
        assert len(records) == 1 and records[0]['id'] == saved['id']
        assert restored_files[saved['attachments'][0]['id']] == b'original\r\n'
        with pytest.raises(ValueError):
            restore(archive, key)
    finally:
        with psycopg.connect(url) as db:
            db.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(target)))
