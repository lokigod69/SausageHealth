import hashlib
import json
import os
import re
import secrets
import time
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.datastructures import UploadFile

from .db import audit, check_password, connect, data_dir, initialize, now, password_hash
from . import intake_ai
from . import loyverse
from . import storage

CATEGORIES = {'sales', 'stock', 'suppliers', 'expenses', 'team', 'walkthrough', 'other'}
MAX_BODY = 105 * 1024 * 1024
MAX_FILE = 50 * 1024 * 1024
ALLOWED_EXT = {'.txt', '.csv', '.tsv', '.xlsx', '.xls', '.pdf', '.png', '.jpg', '.jpeg',
               '.webp', '.heic', '.mp4', '.mov', '.m4a', '.mp3', '.wav', '.ogg', '.webm'}
DUMMY_PASSWORD = password_hash('dummy-password-not-an-account')


class BodyLimit:
    """Enforce a byte limit even when a client streams without Content-Length."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        size = 0
        async def limited():
            nonlocal size
            message = await receive()
            size += len(message.get('body', b''))
            if size > MAX_BODY:
                raise HTTPException(413, 'This upload is too large. Send less than 100 MB at a time.')
            return message
        await self.app(scope, limited, send)


@asynccontextmanager
async def lifespan(app):
    if os.environ.get('SH_ENV') == 'production' and not os.environ.get('SH_ORIGIN', '').startswith('https://'):
        raise RuntimeError('Production requires an HTTPS SH_ORIGIN.')
    initialize()
    if os.environ.get('VERCEL') == '1' and (not storage.cloud_enabled() or not os.environ.get('BLOB_READ_WRITE_TOKEN')
                                         or len(os.environ.get('SH_STORAGE_SIGNING_KEY', '')) < 40):
        raise RuntimeError('Vercel requires private file storage and a signing key.')
    yield


app = FastAPI(title='Sausage Health', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(BodyLimit)


@app.middleware('http')
async def boundary(request: Request, call_next):
    path = request.url.path
    if path.startswith('/api/') and request.method not in ('GET', 'HEAD', 'OPTIONS'):
        expected = os.environ.get('SH_ORIGIN', 'http://127.0.0.1:5180')
        if request.headers.get('origin') != expected or request.headers.get('x-sh-request') != '1':
            return JSONResponse({'detail': 'Please reload the app and try again.'}, status_code=403)
        length = request.headers.get('content-length', '')
        if length and (not length.isdigit() or int(length) > MAX_BODY):
            return JSONResponse({'detail': 'Send less than 100 MB at a time.'}, status_code=413)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['X-Frame-Options'] = 'DENY'
    if path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    if os.environ.get('SH_ENV') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'"
    return response


def public_user(row):
    return {'id': row['id'], 'name': row['name'], 'email': row['email'],
            'role': row['role'], 'stores': json.loads(row['stores'])}


def current_user(request: Request):
    token = request.cookies.get('sh_session', '')
    with connect() as db:
        row = db.execute('''SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id
          WHERE s.token_hash=? AND s.expires>?''', (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
    if not row:
        raise HTTPException(401, 'Sign in to continue.')
    return public_user(row)


def store_allowed(user, store):
    return set(('sausage', 'health') if store == 'both' else (store,)) <= set(user['stores'])


def can_read(user, entry):
    return store_allowed(user, entry['store']) and (user['role'] != 'staff' or entry['author_id'] == user['id'])


def entry_record(db, entry):
    record = dict(entry)
    record.pop('request_key', None)
    record['author_name'] = db.execute('SELECT name FROM users WHERE id=?', (entry['author_id'],)).fetchone()['name']
    record['reviewer_name'] = None
    if entry['reviewed_by']:
        record['reviewer_name'] = db.execute('SELECT name FROM users WHERE id=?', (entry['reviewed_by'],)).fetchone()['name']
    record['attachments'] = [dict(r) for r in db.execute('SELECT id,name,size,sha256 FROM attachments WHERE entry_id=?', (entry['id'],))]
    return record


class Login(BaseModel):
    email: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=256)


@app.get('/api/health')
def health():
    return {'status': 'ok'}


@app.post('/api/login')
def login(body: Login, request: Request):
    email = body.email.strip().lower()
    # Trust the ASGI peer only, never client-supplied forwarding headers.
    address = request.client.host if request.client else 'unknown'
    keys = ['email:' + hashlib.sha256(email.encode()).hexdigest(), 'ip:' + address]
    stamp = time.time()
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        for key in keys:
            row = db.execute('SELECT * FROM login_attempts WHERE key=?', (key,)).fetchone()
            if row and stamp - row['window_start'] < 900 and row['attempts'] >= (10 if key.startswith('email:') else 60):
                raise HTTPException(429, 'Too many attempts. Try again in 15 minutes.')
        user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        valid = check_password(body.password, user['password'] if user else DUMMY_PASSWORD)
        if not user or not valid:
            for key in keys:
                db.execute('''INSERT INTO login_attempts VALUES (?,1,?) ON CONFLICT(key) DO UPDATE SET
                  attempts=CASE WHEN ?-login_attempts.window_start>=900 THEN 1 ELSE login_attempts.attempts+1 END,
                  window_start=CASE WHEN ?-login_attempts.window_start>=900 THEN ? ELSE login_attempts.window_start END''',
                           (key, stamp, stamp, stamp, stamp))
            # Return instead of raising: commit failed-attempt counters.
            return JSONResponse({'detail': 'Email or password is incorrect.'}, status_code=401)
        db.execute('DELETE FROM login_attempts WHERE key=?', (keys[0],))
        db.execute('DELETE FROM sessions WHERE expires<?', (stamp,))
        token = secrets.token_urlsafe(40)
        db.execute('INSERT INTO sessions VALUES (?,?,?)',
                   (hashlib.sha256(token.encode()).hexdigest(), user['id'], stamp + 12 * 3600))
        audit(db, user['id'], 'session.created')
    response = JSONResponse(public_user(user))
    response.set_cookie('sh_session', token, max_age=12*3600, httponly=True,
                        secure=os.environ.get('SH_ENV') == 'production', samesite='strict', path='/')
    return response


@app.post('/api/logout')
def logout(request: Request, user=Depends(current_user)):
    with connect() as db:
        db.execute('DELETE FROM sessions WHERE token_hash=?',
                   (hashlib.sha256(request.cookies.get('sh_session', '').encode()).hexdigest(),))
        audit(db, user['id'], 'session.closed')
    response = JSONResponse({'ok': True})
    response.delete_cookie('sh_session', path='/')
    return response


@app.get('/api/me')
def me(user=Depends(current_user)):
    return user


@app.get('/api/entries')
def entries(user=Depends(current_user)):
    with connect() as db:
        rows = db.execute('SELECT * FROM entries ORDER BY created_at DESC').fetchall()
        return [entry_record(db, row) for row in rows if can_read(user, row)]


@app.post('/api/entries', status_code=201)
async def create_entry(request: Request, user=Depends(current_user)):
    if storage.cloud_enabled():
        raise HTTPException(422, 'Reload the page to use private file uploads.')
    async with request.form(max_files=5, max_fields=12, max_part_size=MAX_FILE) as form:
        store = str(form.get('store', ''))
        category = str(form.get('category', ''))
        title = str(form.get('title', '')).strip()
        notes = str(form.get('notes', '')).strip()
        occurred_on = str(form.get('occurred_on', ''))
        request_key = str(form.get('request_key', ''))
        files = [f for f in form.getlist('files') if isinstance(f, UploadFile) and f.filename]
        if store not in {'sausage', 'health', 'both'} or not store_allowed(user, store):
            raise HTTPException(403, 'Choose a store assigned to your account.')
        if category not in CATEGORIES or not 2 <= len(title) <= 160 or len(notes) > 30000:
            raise HTTPException(422, 'Choose a category, add a title (2–160 characters), and keep notes under 30,000 characters.')
        try:
            date.fromisoformat(occurred_on)
        except ValueError:
            raise HTTPException(422, 'Choose the date this information relates to.')
        if not re.fullmatch(r'[a-zA-Z0-9-]{16,80}', request_key):
            raise HTTPException(422, 'Please reload and submit again.')
        if not notes and not files:
            raise HTTPException(422, 'Add a note or at least one file.')
        if len(files) > 5:
            raise HTTPException(422, 'Send up to five files at a time.')
        with connect() as db:
            previous = db.execute('SELECT * FROM entries WHERE request_key=?', (request_key,)).fetchone()
            if previous:
                if previous['author_id'] != user['id']:
                    raise HTTPException(409, 'Please start a new submission.')
                return entry_record(db, previous)
        entry_id = secrets.token_hex(16)
        saved = []
        total = 0
        try:
            for file in files:
                name = re.sub(r'[\x00-\x1f\x7f]', '', file.filename.replace('\\', '/').split('/')[-1])[:180]
                if Path(name).suffix.lower() not in ALLOWED_EXT:
                    raise HTTPException(422, 'Use a photo, PDF, spreadsheet, text export, audio, or video file.')
                file_id = secrets.token_hex(16)
                target = data_dir() / 'uploads' / file_id
                saved.append({'id': file_id, 'path': target, 'name': name, 'size': 0, 'sha256': ''})
                digest = hashlib.sha256()
                with target.open('xb') as out:
                    while chunk := await file.read(1024 * 1024):
                        saved[-1]['size'] += len(chunk)
                        total += len(chunk)
                        if saved[-1]['size'] > MAX_FILE or total > 100 * 1024 * 1024:
                            raise HTTPException(413, 'Limit each file to 50 MB and each update to 100 MB.')
                        digest.update(chunk)
                        out.write(chunk)
                if saved[-1]['size'] == 0:
                    raise HTTPException(422, 'One of your files is empty. Please remove it and try again.')
                saved[-1]['sha256'] = digest.hexdigest()
            with connect() as db:
                db.execute('BEGIN IMMEDIATE')
                previous = db.execute('SELECT * FROM entries WHERE request_key=?', (request_key,)).fetchone()
                if previous:
                    if previous['author_id'] != user['id']:
                        raise HTTPException(409, 'Please start a new submission.')
                    result = entry_record(db, previous)
                    for item in saved:
                        item['path'].unlink(missing_ok=True)
                    return result
                db.execute('''INSERT INTO entries(id,request_key,store,category,title,notes,occurred_on,created_at,author_id)
                  VALUES (?,?,?,?,?,?,?,?,?)''',
                           (entry_id, request_key, store, category, title, notes, occurred_on, now(), user['id']))
                for item in saved:
                    db.execute('INSERT INTO attachments VALUES (?,?,?,?,?)',
                               (item['id'], entry_id, item['name'], item['size'], item['sha256']))
                audit(db, user['id'], 'entry.created', entry_id, json.dumps({'files': len(saved)}))
                return entry_record(db, db.execute('SELECT * FROM entries WHERE id=?', (entry_id,)).fetchone())
        except BaseException:
            for item in saved:
                item['path'].unlink(missing_ok=True)
            raise


class Review(BaseModel):
    status: str
    note: str = Field(default='', max_length=2000)
    version: int = Field(ge=1)


@app.post('/api/entries/{entry_id}/review')
def review(entry_id: str, body: Review, user=Depends(current_user)):
    if user['role'] not in ('owner', 'manager'):
        raise HTTPException(403, 'A manager reviews submitted information.')
    if body.status not in ('reviewed', 'needs_review'):
        raise HTTPException(422, 'Choose a valid review status.')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        entry = db.execute('SELECT * FROM entries WHERE id=?', (entry_id,)).fetchone()
        if not entry or not can_read(user, entry):
            raise HTTPException(404, 'Update not found.')
        if entry['version'] != body.version:
            raise HTTPException(409, 'Someone updated this record. Close it and reload before reviewing.')
        db.execute('''UPDATE entries SET status=?,reviewed_by=?,reviewed_at=?,review_note=?,version=version+1 WHERE id=?''',
                   (body.status, user['id'], now(), body.note.strip(), entry_id))
        audit(db, user['id'], 'entry.' + body.status, entry_id, body.note.strip())
        return entry_record(db, db.execute('SELECT * FROM entries WHERE id=?', (entry_id,)).fetchone())


@app.get('/api/files/{file_id}')
def download(file_id: str, user=Depends(current_user)):
    with connect() as db:
        file = db.execute('SELECT * FROM attachments WHERE id=?', (file_id,)).fetchone()
        entry = db.execute('SELECT * FROM entries WHERE id=?', (file['entry_id'],)).fetchone() if file else None
        if not entry or not can_read(user, entry):
            raise HTTPException(404, 'File not found.')
        audit(db, user['id'], 'file.downloaded', entry['id'], file['id'])
    if storage.cloud_enabled():
        return RedirectResponse('/api/storage?grant=' + storage.grant(file_id, 'get'), status_code=303,
                                headers={'Referrer-Policy': 'no-referrer', 'Cache-Control': 'no-store'})
    target = data_dir() / 'uploads' / file['id']
    if not target.is_file():
        raise HTTPException(404, 'Original file is unavailable. Ask the technical owner to check the backup.')
    return FileResponse(target, filename=file['name'], media_type='application/octet-stream')


@app.get('/api/export')
def export(user=Depends(current_user)):
    if user['role'] != 'owner':
        raise HTTPException(403, 'Only the technical owner can export the collection.')
    with connect() as db:
        audit(db, user['id'], 'collection.exported')
    return JSONResponse({'schema_version': 1, 'exported_at': now(), 'entries': entries(user)},
                        headers={'Content-Disposition': 'attachment; filename="sausage-health-collection.json"'})


@app.get('/api/system')
def system(user=Depends(current_user)):
    return {'phase': 'collect', 'ai': 'ready' if intake_ai.configured() else 'not_connected',
            'loyverse': loyverse.state(),
            'storage': 'server', 'uploads': 'originals_preserved', 'max_file_mb': 50,
            'environment': os.environ.get('SH_ENV', 'development'),
            'upload_mode': 'direct' if storage.cloud_enabled() else 'multipart'}


def catalogue_reader(user):
    """Items mirror a whole POS account, so it follows the review roles, not own-submission access."""
    if user['role'] not in ('owner', 'manager'):
        raise HTTPException(403, 'The item list is available to the owner and store operators.')
    return user


@app.get('/api/loyverse/items')
def loyverse_items(user=Depends(current_user)):
    return loyverse.latest(catalogue_reader(user))


@app.post('/api/loyverse/refresh')
def loyverse_refresh(user=Depends(current_user)):
    return loyverse.sync(catalogue_reader(user))


@app.get('/api/cron/loyverse')
def loyverse_scheduled(request: Request):
    """The once-a-day read. Unknown callers get the same 404 as any unknown path."""
    secret = os.environ.get('CRON_SECRET', '')
    supplied = request.headers.get('authorization', '')
    if not secret or not secrets.compare_digest(supplied, 'Bearer ' + secret):
        raise HTTPException(404, 'Endpoint not found.')
    if not loyverse.configured():
        return {'status': 'skipped', 'reason': 'Loyverse is not connected in this environment.'}
    return loyverse.sync(loyverse.system_actor(), scheduled=True)


class FileSpec(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    size: int = Field(ge=1, le=MAX_FILE)
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')


class Submission(BaseModel):
    request_key: str = Field(pattern=r'^[a-zA-Z0-9-]{16,80}$')
    store: str
    category: str
    title: str = Field(min_length=2, max_length=160)
    notes: str = Field(default='', max_length=30000)
    occurred_on: str
    files: list[FileSpec] = Field(default_factory=list, max_length=5)


@app.post('/api/upload-intents')
def upload_intent(body: Submission, user=Depends(current_user)):
    if not storage.cloud_enabled():
        raise HTTPException(404, 'Endpoint not found.')
    if body.store not in {'sausage', 'health', 'both'} or not store_allowed(user, body.store):
        raise HTTPException(403, 'Choose a store assigned to your account.')
    if body.category not in CATEGORIES or len(body.title.strip()) < 2 or (not body.notes.strip() and not body.files):
        raise HTTPException(422, 'Add a title and a note or file.')
    try:
        date.fromisoformat(body.occurred_on)
    except ValueError:
        raise HTTPException(422, 'Choose the date this information relates to.')
    for file in body.files:
        file.name = re.sub(r'[\x00-\x1f\x7f]', '', file.name.replace('\\', '/').split('/')[-1])[:180]
        if Path(file.name).suffix.lower() not in ALLOWED_EXT:
            raise HTTPException(422, 'Use a photo, PDF, spreadsheet, text export, audio, or video file.')
    total = sum(f.size for f in body.files)
    if total > 100 * 1024 * 1024:
        raise HTTPException(413, 'Send less than 100 MB at a time.')
    payload = body.model_dump()
    payload['notes'], payload['title'] = body.notes.strip(), body.title.strip()
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    digest = hashlib.sha256(encoded.encode()).hexdigest()
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        previous = db.execute('SELECT * FROM upload_intents WHERE request_key=?', (body.request_key,)).fetchone()
        if previous:
            if previous['author_id'] != user['id'] or previous['payload_hash'] != digest:
                raise HTTPException(409, 'This submission has different contents. Close it and start a new update.')
            if previous['entry_id']:
                return {'entry': entry_record(db, db.execute('SELECT * FROM entries WHERE id=?', (previous['entry_id'],)).fetchone())}
            if previous['expires'] < time.time():
                raise HTTPException(409, 'This upload expired. Close it and start a new update.')
            intent_id, files, expires = previous['id'], json.loads(previous['files']), previous['expires']
        else:
            # Bounded pilot usage; reservations count even if a browser never finalizes.
            reservations = db.execute('SELECT files,author_id,created_at FROM upload_intents').fetchall()
            reserved = sum(sum(f['size'] for f in json.loads(r['files'])) for r in reservations)
            if reserved + total > int(os.environ.get('SH_STORAGE_MAX_BYTES', str(1024 ** 3))):
                raise HTTPException(429, 'The collection storage limit has been reached. Contact the owner.')
            if sum(r['author_id'] == user['id'] and r['created_at'][:10] == now()[:10] for r in reservations) >= 30:
                raise HTTPException(429, 'The daily upload limit has been reached. Try again tomorrow.')
            intent_id, expires = secrets.token_hex(16), time.time() + 24 * 3600
            files = [{'id': secrets.token_hex(16), **f.model_dump()} for f in body.files]
            db.execute('INSERT INTO upload_intents VALUES (?,?,?,?,?,?,?,?,?)',
                       (intent_id, body.request_key, user['id'], encoded, digest, json.dumps(files), expires, now(), None))
            audit(db, user['id'], 'upload.reserved', detail=intent_id)
        return {'id': intent_id, 'files': [dict(file, grant=storage.grant(file['id'], 'put', file['size'], expires)) for file in files]}


@app.post('/api/upload-intents/{intent_id}/finalize', status_code=201)
def finalize_upload(intent_id: str, user=Depends(current_user)):
    if not storage.cloud_enabled():
        raise HTTPException(404, 'Endpoint not found.')
    with connect() as db:
        intent = db.execute('SELECT * FROM upload_intents WHERE id=?', (intent_id,)).fetchone()
        if not intent or intent['author_id'] != user['id']:
            raise HTTPException(404, 'Upload not found.')
        payload = json.loads(intent['payload'])
        if not store_allowed(user, payload['store']):
            raise HTTPException(403, 'This store is not assigned to your account.')
        if intent['entry_id']:
            return entry_record(db, db.execute('SELECT * FROM entries WHERE id=?', (intent['entry_id'],)).fetchone())
        if intent['expires'] < time.time():
            raise HTTPException(409, 'This upload expired. Close it and start a new update.')
        files = json.loads(intent['files'])
    # Provider-enforced no-overwrite paths make verification stable while DB work runs.
    for file in files:
        try:
            raw = storage.read_original(file['id'], file['size'])
            if hashlib.sha256(raw).hexdigest() != file['sha256']:
                raise ValueError('Checksum mismatch')
            del raw
        except Exception:
            raise HTTPException(503, 'The original file could not be verified. Keep this page open and retry.')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        current = db.execute('SELECT * FROM upload_intents WHERE id=?', (intent_id,)).fetchone()
        if current['entry_id']:
            return entry_record(db, db.execute('SELECT * FROM entries WHERE id=?', (current['entry_id'],)).fetchone())
        if current['expires'] < time.time():
            raise HTTPException(409, 'This upload expired. Close it and start a new update.')
        entry_id = secrets.token_hex(16)
        db.execute('''INSERT INTO entries(id,request_key,store,category,title,notes,occurred_on,created_at,author_id)
                      VALUES (?,?,?,?,?,?,?,?,?)''',
                   (entry_id, payload['request_key'], payload['store'], payload['category'], payload['title'],
                    payload['notes'], payload['occurred_on'], now(), user['id']))
        for file in files:
            db.execute('INSERT INTO attachments VALUES (?,?,?,?,?)',
                       (file['id'], entry_id, file['name'], file['size'], file['sha256']))
        db.execute('UPDATE upload_intents SET entry_id=? WHERE id=?', (entry_id, intent_id))
        audit(db, user['id'], 'entry.created', entry_id, json.dumps({'files': len(files), 'storage': 'private'}))
        return entry_record(db, db.execute('SELECT * FROM entries WHERE id=?', (entry_id,)).fetchone())


def ai_entry(entry_id, user):
    if user['role'] not in ('owner', 'manager'):
        raise HTTPException(403, 'Only the owner or store operator can prepare AI drafts.')
    with connect() as db:
        entry = db.execute('SELECT * FROM entries WHERE id=?', (entry_id,)).fetchone()
        if not entry or not can_read(user, entry):
            raise HTTPException(404, 'Update not found.')
    return entry


@app.post('/api/entries/{entry_id}/extract')
def extract_entry(entry_id: str, user=Depends(current_user)):
    return intake_ai.extract(ai_entry(entry_id, user), user)


@app.get('/api/entries/{entry_id}/draft')
def latest_draft(entry_id: str, user=Depends(current_user)):
    ai_entry(entry_id, user)
    with connect() as db:
        row = db.execute('SELECT id,status,model,result,error FROM ai_runs WHERE entry_id=? ORDER BY started_at DESC LIMIT 1', (entry_id,)).fetchone()
    if not row:
        return None
    result = dict(row)
    result['result'] = json.loads(result['result']) if result['result'] else None
    return result


@app.get('/api/audit')
def audit_log(user=Depends(current_user)):
    if user['role'] != 'owner':
        raise HTTPException(403, 'Only the technical owner can view the full audit trail.')
    with connect() as db:
        return [dict(r) for r in db.execute('''SELECT a.*,u.name AS actor_name FROM audit a
          JOIN users u ON u.id=a.actor_id ORDER BY a.id DESC LIMIT 100''')]


@app.get('/api/{path:path}')
def unknown_api(path: str):
    raise HTTPException(404, 'Endpoint not found.')


if Path('dist').is_dir():
    app.mount('/', StaticFiles(directory='dist', html=True), name='frontend')
