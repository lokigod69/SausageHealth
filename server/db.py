import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def data_dir():
    path = Path(os.environ.get('SH_DATA_DIR', '.data')).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def connect():
    db = sqlite3.connect(data_dir() / 'sausagehealth.sqlite', timeout=20)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def initialize():
    (data_dir() / 'uploads').mkdir(exist_ok=True)
    with connect() as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
          id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
          password TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('owner','manager','staff')),
          stores TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
          token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS entries (
          id TEXT PRIMARY KEY, request_key TEXT NOT NULL UNIQUE,
          store TEXT NOT NULL CHECK(store IN ('sausage','health','both')),
          category TEXT NOT NULL, title TEXT NOT NULL, notes TEXT NOT NULL,
          occurred_on TEXT NOT NULL, created_at TEXT NOT NULL,
          author_id TEXT NOT NULL REFERENCES users(id), status TEXT NOT NULL DEFAULT 'needs_review',
          reviewed_by TEXT REFERENCES users(id), reviewed_at TEXT, review_note TEXT NOT NULL DEFAULT '',
          version INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS attachments (
          id TEXT PRIMARY KEY, entry_id TEXT NOT NULL REFERENCES entries(id),
          name TEXT NOT NULL, size INTEGER NOT NULL, sha256 TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit (
          id INTEGER PRIMARY KEY, actor_id TEXT NOT NULL REFERENCES users(id),
          action TEXT NOT NULL, entry_id TEXT, detail TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS login_attempts (
          key TEXT PRIMARY KEY, attempts INTEGER NOT NULL, window_start REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS entries_by_author ON entries(author_id);
        CREATE TABLE IF NOT EXISTS ai_runs (
          id TEXT PRIMARY KEY, entry_id TEXT NOT NULL REFERENCES entries(id), actor_id TEXT NOT NULL REFERENCES users(id),
          status TEXT NOT NULL, model TEXT NOT NULL, started_at TEXT NOT NULL, result TEXT, error TEXT,
          source_digest TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ai_runs_by_entry ON ai_runs(entry_id,started_at);
        PRAGMA user_version=1;
        ''')


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return salt + ':' + digest


def check_password(password, stored):
    return secrets.compare_digest(password_hash(password, stored.split(':')[0]), stored)


def add_user(email, name, role, stores, password):
    if role not in ('owner', 'manager', 'staff') or not stores or not set(stores) <= {'sausage', 'health'}:
        raise ValueError('Choose a valid role and at least one store.')
    if len(password) < 12 or len(password) > 256:
        raise ValueError('Use a password of 12–256 characters.')
    if not email.strip() or not name.strip():
        raise ValueError('Email and name are required.')
    with connect() as db:
        db.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?)', (
            secrets.token_hex(16), email.strip().lower(), name.strip(), password_hash(password),
            role, json.dumps(stores), now()))


def audit(db, actor, action, entry=None, detail=''):
    db.execute('INSERT INTO audit(actor_id,action,entry_id,detail,created_at) VALUES (?,?,?,?,?)',
               (actor, action, entry, detail, now()))


def reset_password(email, password):
    if not 12 <= len(password) <= 256:
        raise ValueError('Use a password of 12–256 characters.')
    with connect() as db:
        row = db.execute('SELECT id FROM users WHERE email=?', (email.strip().lower(),)).fetchone()
        if not row:
            raise ValueError('Account not found.')
        db.execute('UPDATE users SET password=? WHERE id=?', (password_hash(password), row['id']))
        db.execute('DELETE FROM sessions WHERE user_id=?', (row['id'],))
        audit(db, row['id'], 'credential.reset_by_server_admin')
