"""Long-lived sessions for a shop tablet, paired once and revocable afterwards.

A tablet standing on the counter all day should not be logged out every twelve
hours. But a credential that never expires and cannot be withdrawn is a different
thing entirely: if the tablet is lost, the access goes with it. So a device
session does not expire, and the owner can end it from the workspace at any time.

Pairing is deliberately a two-step: the owner asks for a code, and that code is
typed on the tablet. The long-lived token is only ever set as a cookie on the
device that redeemed it, so it never travels through a chat, an email or a URL.
The code is short-lived, single use, and guesses are counted.
"""
import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from .db import audit, connect, now

# Letters and digits that cannot be misread on a tablet screen: no O/0, I/1, S/5.
ALPHABET = 'ABCDEFGHJKLMNPQRTUVWXYZ2346789'
CODE_LENGTH = 10
CODE_MINUTES = 15
MAX_ATTEMPTS = 10
SEEN_EVERY_SECONDS = 3600


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def pairing_code():
    return ''.join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def tidy(value):
    """Accept the code however it was typed: spacing and case do not matter."""
    return ''.join(character for character in (value or '').upper()
                   if character in ALPHABET)


def start_pairing(actor, name, acts_as):
    """Create a pending device and return the code to type on the tablet once."""
    if actor['role'] != 'owner':
        raise HTTPException(403, 'Only the technical owner can pair a device.')
    label = (name or '').strip()[:60]
    if len(label) < 2:
        raise HTTPException(422, 'Give the device a name you will recognise later.')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        target = db.execute('SELECT id,name,role FROM users WHERE id=?', (acts_as,)).fetchone()
        if not target:
            raise HTTPException(422, 'Choose an account for the tablet to act as.')
        if target['role'] == 'owner':
            # A counter tablet does not need to export the collection or read the
            # audit trail, and a lost one should not be able to.
            raise HTTPException(422, 'Pair the tablet to a store operator or team account, not the owner.')
        code = pairing_code()
        device_id = secrets.token_hex(16)
        db.execute('''INSERT INTO devices(id,name,token_hash,user_id,created_at,created_by,
                      last_seen,revoked_at,pairing_hash,pairing_expires,attempts)
                      VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                   (device_id, label, None, target['id'], now(), actor['id'], None, None,
                    digest(code), time.time() + CODE_MINUTES * 60, 0))
        audit(db, actor['id'], 'device.pairing_started', None, device_id)
    return {'id': device_id, 'name': label, 'acts_as': target['name'],
            'code': code, 'expires_in_minutes': CODE_MINUTES}


def redeem(code):
    """Exchange a typed code for the device's long-lived token, once."""
    cleaned = tidy(code)
    if len(cleaned) != CODE_LENGTH:
        raise HTTPException(422, 'That code is not complete. Check it and type it again.')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('''SELECT * FROM devices WHERE pairing_hash=? AND token_hash IS NULL
                            AND revoked_at IS NULL''', (digest(cleaned),)).fetchone()
        if not row:
            raise HTTPException(404, 'That code is not valid. Ask for a new one.')
        if row['pairing_expires'] < time.time():
            raise HTTPException(409, 'That code has expired. Ask for a new one.')
        if row['attempts'] >= MAX_ATTEMPTS:
            raise HTTPException(429, 'Too many attempts for this code. Ask for a new one.')
        token = secrets.token_urlsafe(48)
        db.execute('''UPDATE devices SET token_hash=?,pairing_hash=NULL,pairing_expires=NULL,
                      last_seen=? WHERE id=?''', (digest(token), now(), row['id']))
        audit(db, row['user_id'], 'device.paired', None, row['id'])
    return row['id'], token


def count_attempt(code):
    """A wrong guess is counted against the code it was aimed at, if it names one."""
    cleaned = tidy(code)
    if len(cleaned) != CODE_LENGTH:
        return
    with connect() as db:
        db.execute('UPDATE devices SET attempts=attempts+1 WHERE pairing_hash=?', (digest(cleaned),))


def holder(token):
    """The account a device token speaks for, or None. Never raises on a bad token."""
    if not token:
        return None
    with connect() as db:
        row = db.execute('''SELECT d.id AS device_id, d.name AS device_name, d.last_seen, u.*
                            FROM devices d JOIN users u ON u.id = d.user_id
                            WHERE d.token_hash=? AND d.revoked_at IS NULL''',
                         (digest(token),)).fetchone()
        if not row:
            return None
        # Writing on every request would turn a read into a write; once an hour is
        # enough to tell a working tablet from a forgotten one.
        stale = row['last_seen'] is None or (
            datetime.now(timezone.utc) - datetime.fromisoformat(row['last_seen'])
        ).total_seconds() > SEEN_EVERY_SECONDS
        if stale:
            db.execute('UPDATE devices SET last_seen=? WHERE id=?', (now(), row['device_id']))
    return row


def listing(actor):
    if actor['role'] != 'owner':
        raise HTTPException(403, 'Only the technical owner can see paired devices.')
    with connect() as db:
        rows = db.execute('''SELECT d.id,d.name,d.created_at,d.last_seen,d.revoked_at,
                             d.token_hash IS NULL AS pending, u.name AS acts_as
                             FROM devices d JOIN users u ON u.id=d.user_id
                             ORDER BY d.created_at DESC''').fetchall()
    return [{'id': row['id'], 'name': row['name'], 'acts_as': row['acts_as'],
             'created_at': row['created_at'], 'last_seen': row['last_seen'],
             'revoked': row['revoked_at'] is not None,
             'paired': not bool(row['pending'])} for row in rows]


def revoke(actor, device_id):
    if actor['role'] != 'owner':
        raise HTTPException(403, 'Only the technical owner can end a device session.')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT * FROM devices WHERE id=?', (device_id,)).fetchone()
        if not row:
            raise HTTPException(404, 'Device not found.')
        if row['revoked_at'] is not None:
            return {'ok': True, 'already': True}
        db.execute('UPDATE devices SET revoked_at=?,token_hash=NULL,pairing_hash=NULL WHERE id=?',
                   (now(), device_id))
        audit(db, actor['id'], 'device.revoked', None, device_id)
    return {'ok': True, 'already': False}
