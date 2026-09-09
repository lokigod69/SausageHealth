"""Encrypted database + immutable originals snapshot. Run from a trusted admin machine."""
import argparse
import hashlib
import io
import json
import os
import secrets
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from .db import connect, initialize, now, postgres_enabled
from . import storage

MAGIC = b'SHBACKUP2\x00'
TABLES = ('users', 'entries', 'attachments', 'audit', 'ai_runs', 'upload_intents')


def backup(destination, key_file):
    if not postgres_enabled() or not storage.cloud_enabled():
        raise ValueError('Cloud backup requires Postgres and private storage.')
    destination, key_file = Path(destination), Path(key_file)
    if destination.exists() or not key_file.is_file():
        raise ValueError('Choose a new backup file and an existing private key file.')
    key = bytes.fromhex(key_file.read_text().strip())
    with connect() as db:
        db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        tables = {table: [dict(row) for row in db.execute('SELECT * FROM ' + table +
                  (' WHERE entry_id IS NOT NULL' if table == 'upload_intents' else ''))] for table in TABLES}
    manifest = {'version': 2, 'created_at': now(), 'tables': tables,
                'source_schema': os.environ.get('SH_DATABASE_SCHEMA', 'public'),
                'source_prefix': os.environ.get('SH_BLOB_PREFIX', 'pilot')}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json', json.dumps(manifest))
        for file in tables['attachments']:
            raw = storage.read_original(file['id'], file['size'])
            if hashlib.sha256(raw).hexdigest() != file['sha256']:
                raise ValueError('Original checksum mismatch; backup aborted.')
            archive.writestr('originals/' + file['id'], raw)
    nonce = secrets.token_bytes(12)
    encrypted = MAGIC + nonce + AESGCM(key).encrypt(nonce, buffer.getvalue(), MAGIC)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as out:
        out.write(encrypted)
    return {'attachment_count': len(tables['attachments']), 'entry_count': len(tables['entries']),
            'archive_sha256': hashlib.sha256(encrypted).hexdigest(), 'bytes': len(encrypted)}


def restore(source, key_file):
    if not postgres_enabled() or not storage.cloud_enabled():
        raise ValueError('Cloud restore requires Postgres and private storage.')
    encrypted = Path(source).read_bytes()
    if not encrypted.startswith(MAGIC):
        raise ValueError('Unsupported backup format.')
    nonce = encrypted[len(MAGIC):len(MAGIC) + 12]
    key = bytes.fromhex(Path(key_file).read_text().strip())
    raw_archive = AESGCM(key).decrypt(nonce, encrypted[len(MAGIC) + 12:], MAGIC)
    with zipfile.ZipFile(io.BytesIO(raw_archive)) as archive:
        manifest = json.loads(archive.read('manifest.json'))
        if manifest['version'] != 2 or set(manifest['tables']) != set(TABLES):
            raise ValueError('Unsupported backup schema.')
        # Refuse in-place restores even when the source database currently appears empty.
        if os.environ.get('SH_DATABASE_SCHEMA', 'public') == manifest['source_schema'] or \
                os.environ.get('SH_BLOB_PREFIX', 'pilot') == manifest['source_prefix']:
            raise ValueError('Restore requires a different empty database schema and storage prefix.')
        initialize()
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            for table in TABLES:
                if db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]:
                    raise ValueError('Restore target is not empty.')
            # Check and write all files before committing database references.
            for file in manifest['tables']['attachments']:
                raw = archive.read('originals/' + file['id'])
                if len(raw) != file['size'] or hashlib.sha256(raw).hexdigest() != file['sha256']:
                    raise ValueError('Original checksum mismatch.')
                storage.write_original(file['id'], raw)
                if hashlib.sha256(storage.read_original(file['id'], file['size'])).hexdigest() != file['sha256']:
                    raise ValueError('Restored original could not be verified.')
            # Fixed SQL columns come from our schema, never archive-controlled SQL strings.
            for table in TABLES:
                columns = list(db.execute('SELECT * FROM ' + table + ' LIMIT 0').description)
                names = [column.name for column in columns]
                query = 'INSERT INTO ' + table + '(' + ','.join(names) + ') VALUES (' + ','.join('?' for _ in names) + ')'
                for row in manifest['tables'][table]:
                    if set(row) != set(names):
                        raise ValueError('Backup columns do not match the target schema.')
                    db.execute(query, tuple(row[name] for name in names))
            db.execute("SELECT setval(pg_get_serial_sequence('audit','id'), COALESCE((SELECT MAX(id) FROM audit), 1), EXISTS(SELECT 1 FROM audit))")
        return {'entry_count': len(manifest['tables']['entries']), 'attachment_count': len(manifest['tables']['attachments']),
                'sessions_restored': 0}


def cleanup_expired():
    if not storage.cloud_enabled():
        raise ValueError('Private cloud storage is required.')
    import time
    count = 0
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        for intent in db.execute('SELECT * FROM upload_intents WHERE entry_id IS NULL AND expires<?', (time.time() - 600,)).fetchall():
            for file in json.loads(intent['files']):
                if db.execute('SELECT 1 FROM attachments WHERE id=?', (file['id'],)).fetchone():
                    raise ValueError('A committed original must not be removed.')
                storage.delete_uncommitted(file['id'])
            db.execute('DELETE FROM upload_intents WHERE id=?', (intent['id'],))
            count += 1
    return {'expired_uploads_removed': count}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['backup', 'restore', 'cleanup-expired'])
    parser.add_argument('archive', nargs='?')
    parser.add_argument('--key-file')
    args = parser.parse_args()
    print(json.dumps(cleanup_expired() if args.command == 'cleanup-expired' else
                     (backup if args.command == 'backup' else restore)(args.archive, args.key_file)))
