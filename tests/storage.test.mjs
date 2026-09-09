import test from 'node:test';
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { verifyGrant } from '../api/storage.mjs';

const key = 'test-only-' + '7'.repeat(48);
const now = Date.now();
const payload = { v: 1, operation: 'put', pathname: 'pilot/originals/' + 'a'.repeat(32), size: 100, expires: Math.floor(now / 1000) + 60 };
function token(data) {
  const encoded = Buffer.from(JSON.stringify(data)).toString('base64url');
  return encoded + '.' + createHmac('sha256', key).update(encoded).digest('hex');
}
test('private file grants reject tampering, expiry, excessive size, operation and path scope', () => {
  assert.deepEqual(verifyGrant(token(payload), key, 'pilot', now), payload);
  for (const change of [{ expires: 1 }, { expires: Math.floor(now / 1000) + 1000 }, { operation: 'delete' },
    { pathname: '*' }, { pathname: 'other/originals/' + 'a'.repeat(32) }, { size: 52_428_801 }, { size: 0 }]) {
    assert.throws(() => verifyGrant(token({ ...payload, ...change }), key, 'pilot', now));
  }
  assert.throws(() => verifyGrant(token(payload) + '.extra', key));
  assert.throws(() => verifyGrant(token(payload), 'wrong-key'.repeat(10)));
});
