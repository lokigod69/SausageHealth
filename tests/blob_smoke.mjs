// Explicit live-provider smoke; only its own random paths are created/deleted.
import assert from 'node:assert/strict';
import { randomBytes, createHash } from 'node:crypto';
import { del, head, get } from '@vercel/blob';
import { signGrant } from '../api/storage.mjs';
const pathname = 'validation-' + randomBytes(8).toString('hex') + '/originals/' + randomBytes(16).toString('hex');
const raw = randomBytes(6 * 1024 * 1024);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
try {
  const put = await signGrant({ operation: 'put', pathname, size: raw.length, expires: Math.floor(Date.now() / 1000) + 120 });
  const sent = await fetch(put.presignedUrl, { method: 'PUT', headers: { 'content-type': 'application/octet-stream' }, body: raw });
  assert.equal(sent.ok, true, `Private PUT failed: ${sent.status}`);
  const duplicate = await fetch(put.presignedUrl, { method: 'PUT', headers: { 'content-type': 'application/octet-stream' }, body: raw });
  assert.equal(duplicate.ok, false, 'Original was overwritten');
  const detail = await duplicate.json();
  const metadata = await head(pathname);
  assert.equal(metadata.size, raw.length);
  assert.equal((await fetch(metadata.url)).ok, false, 'Anonymous original access succeeded');
  const signed = await signGrant({ operation: 'get', pathname, expires: Math.floor(Date.now() / 1000) + 60 });
  const downloaded = await fetch(signed.presignedUrl);
  assert.equal(downloaded.ok, true);
  assert.equal(hash(Buffer.from(await downloaded.arrayBuffer())), hash(raw));
  const verified = await get(pathname, { access: 'private', useCache: false });
  assert.ok(verified);
  console.log(JSON.stringify({ private_upload: true, bytes: raw.length, signed_download_checksum: true,
    anonymous_denied: true, overwrite_denied: true, duplicate_status: duplicate.status,
    duplicate_code: detail.error?.code || detail.code }));
} finally {
  await del(pathname);
}
