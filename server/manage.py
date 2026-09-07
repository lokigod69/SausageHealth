"""Administration stays out of employee flows. Passwords are entered privately."""
import argparse
import getpass
import json
import secrets
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import tempfile
from contextlib import closing
import os

from .db import add_user, connect, data_dir, initialize, reset_password


def backup(destination):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError('Choose a new backup filename; existing backups are never overwritten.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        snapshot = Path(temp) / 'sausagehealth.sqlite'
        with connect() as source, closing(sqlite3.connect(snapshot)) as target:
            source.backup(target)
            assert target.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            files = target.execute('SELECT id,sha256 FROM attachments').fetchall()
        partial = destination.with_name(destination.name + '.partial')
        with zipfile.ZipFile(partial, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(snapshot, 'sausagehealth.sqlite')
            for file_id, checksum in files:
                path = data_dir() / 'uploads' / file_id
                import hashlib
                if hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
                    raise ValueError('Attachment checksum mismatch. Backup incomplete: ' + file_id)
                archive.write(path, 'uploads/' + file_id)
            archive.writestr('manifest.json', json.dumps({'schema_version': 1, 'created_at': datetime.now(timezone.utc).isoformat(), 'attachment_count': len(files)}))
        # A failed archive remains visibly incomplete; never overwrite a known backup.
        os.link(partial, destination)
        partial.unlink()
    return destination


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    add = sub.add_parser('add-user')
    add.add_argument('--email', required=True)
    add.add_argument('--name', required=True)
    add.add_argument('--role', choices=['owner', 'manager', 'staff'], required=True)
    add.add_argument('--stores', nargs='+', choices=['sausage', 'health'], default=['sausage', 'health'])
    sub.add_parser('init')
    sub.add_parser('local-preview')
    reset = sub.add_parser('reset-password')
    reset.add_argument('--email', required=True)
    sub.add_parser('revoke-all-sessions')
    snap = sub.add_parser('backup')
    snap.add_argument('destination')
    args = parser.parse_args()
    initialize()
    if args.command in ('add-user', 'reset-password'):
        password = getpass.getpass('New password (12+ characters): ')
        if password != getpass.getpass('Confirm password: '):
            raise ValueError('Passwords did not match.')
        if args.command == 'add-user':
            add_user(args.email, args.name, args.role, args.stores, password)
            print('Account created for ' + args.name)
        else:
            reset_password(args.email, password)
            print('Password reset and account sessions revoked.')
    elif args.command == 'revoke-all-sessions':
        with connect() as db:
            db.execute('DELETE FROM sessions')
        print('All sessions revoked. Users must sign in again.')
    elif args.command == 'local-preview':
        import os
        if os.environ.get('SH_ENV') == 'production':
            raise ValueError('Local preview accounts are not available in production.')
        credential = data_dir() / 'preview-login.json'
        with connect() as db:
            exists = db.execute('SELECT 1 FROM users WHERE email=?', ('owner@sausagehealth.local',)).fetchone()
        if exists:
            print('Preview account already exists. Credentials remain in .data/preview-login.json.')
            return
        password = secrets.token_urlsafe(24)
        add_user('owner@sausagehealth.local', 'Michael', 'owner', ['sausage', 'health'], password)
        credential.write_text(json.dumps({'email': 'owner@sausagehealth.local', 'password': password}), encoding='utf-8')
        credential.chmod(0o600)
        print('Local preview account created. Credentials saved privately in .data/preview-login.json.')
    elif args.command == 'backup':
        print(backup(args.destination))
    else:
        print('Database initialized.')


if __name__ == '__main__':
    main()
