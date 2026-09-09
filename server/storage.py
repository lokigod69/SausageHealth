"""Private originals. Cloud permissions are short lived, file specific and signed."""
import base64
import hashlib
import hmac
import json
import os
import re
import time

from .db import data_dir


def cloud_enabled():
    return os.environ.get('SH_STORAGE') == 'blob'


def pathname(file_id):
    if not re.fullmatch(r'[a-f0-9]{32}', file_id):
        raise ValueError('Invalid file identifier.')
    prefix = os.environ.get('SH_BLOB_PREFIX', 'pilot')
    if not re.fullmatch(r'[a-z0-9-]{1,60}', prefix):
        raise ValueError('Invalid storage prefix.')
    return f'{prefix}/originals/{file_id}'


def grant(file_id, operation, size=0, expires=None):
    secret = os.environ.get('SH_STORAGE_SIGNING_KEY', '')
    if len(secret) < 40:
        raise RuntimeError('Storage signing key is not configured.')
    expiry = min(int(expires or time.time() + 300), int(time.time()) + (300 if operation == 'put' else 60))
    payload = {'v': 1, 'operation': operation, 'pathname': pathname(file_id), 'size': size, 'expires': expiry}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(',', ':')).encode()).rstrip(b'=').decode()
    signature = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return encoded + '.' + signature


def read_original(file_id, expected_size=None):
    if not cloud_enabled():
        return (data_dir() / 'uploads' / file_id).read_bytes()
    from vercel import blob
    path = pathname(file_id)
    info = blob.head(path)
    if not 0 < info.size <= 50 * 1024 * 1024 or (expected_size is not None and info.size != expected_size):
        raise ValueError('The uploaded file size does not match.')
    result = blob.get(path, access='private', use_cache=False, timeout=60)
    if result.status_code != 200 or len(result.content) != info.size:
        raise ValueError('The original is incomplete.')
    return result.content


def write_original(file_id, raw):
    if cloud_enabled():
        from vercel import blob
        return blob.put(pathname(file_id), raw, access='private', content_type='application/octet-stream',
                        add_random_suffix=False, overwrite=False)
    (data_dir() / 'uploads' / file_id).write_bytes(raw)


def delete_uncommitted(file_id):
    if cloud_enabled():
        from vercel import blob
        blob.delete(pathname(file_id))
    else:
        (data_dir() / 'uploads' / file_id).unlink(missing_ok=True)
