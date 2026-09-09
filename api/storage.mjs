import { createHmac, timingSafeEqual } from 'node:crypto';
import { issueSignedToken, presignUrl } from '@vercel/blob';

export function verifyGrant(value, secret, prefix = 'pilot', now = Date.now()) {
  if (!secret || secret.length < 40 || typeof value !== 'string' || value.length > 1500) throw new Error('Invalid permission');
  const [encoded, signature, extra] = value.split('.');
  if (extra !== undefined || !/^[a-f0-9]{64}$/.test(signature ?? '')) throw new Error('Invalid permission');
  const expected = createHmac('sha256', secret).update(encoded).digest();
  if (!timingSafeEqual(expected, Buffer.from(signature, 'hex'))) throw new Error('Invalid permission');
  const grant = JSON.parse(Buffer.from(encoded, 'base64url').toString());
  if (grant.v !== 1 || !['get', 'put'].includes(grant.operation) ||
      !Number.isInteger(grant.expires) || grant.expires * 1000 <= now || grant.expires * 1000 > now + 301000 ||
      !/^[a-z0-9-]{1,60}$/.test(prefix) ||
      !new RegExp(`^${prefix}/originals/[a-f0-9]{32}$`).test(grant.pathname) ||
      (grant.operation === 'put' && (!Number.isInteger(grant.size) || grant.size < 1 || grant.size > 50 * 1024 * 1024))) {
    throw new Error('Invalid permission');
  }
  return grant;
}

export async function signGrant(grant) {
  const upload = grant.operation === 'put';
  const restrictions = upload ? { allowedContentTypes: ['application/octet-stream'], maximumSizeInBytes: grant.size } : {};
  const token = await issueSignedToken({ pathname: grant.pathname, operations: [grant.operation],
    validUntil: grant.expires * 1000, ...restrictions });
  return presignUrl(token, { operation: grant.operation, pathname: grant.pathname, access: 'private',
    validUntil: grant.expires * 1000, ...(upload ? { ...restrictions, addRandomSuffix: false, allowOverwrite: false } : {}) });
}

export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Referrer-Policy', 'no-referrer');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  if (process.env.SH_STORAGE !== 'blob') return res.status(503).json({ detail: 'File storage is unavailable.' });
  if (req.method !== 'POST' && req.method !== 'GET') return res.status(405).end();
  if (req.method === 'POST' && (req.headers.origin !== process.env.SH_ORIGIN || req.headers['x-sh-request'] !== '1')) {
    return res.status(403).json({ detail: 'Please reload and try again.' });
  }
  let grant;
  try {
    const value = req.method === 'GET' ? req.query.grant : req.body?.grant;
    grant = verifyGrant(value, process.env.SH_STORAGE_SIGNING_KEY, process.env.SH_BLOB_PREFIX || 'pilot');
    if (grant.operation !== (req.method === 'POST' ? 'put' : 'get')) throw new Error('Invalid permission');
  } catch {
    return res.status(403).json({ detail: 'File access expired. Try again from the collection.' });
  }
  try {
    const { presignedUrl } = await signGrant(grant);
    if (req.method === 'GET') return res.redirect(303, presignedUrl);
    return res.status(200).json({ url: presignedUrl });
  } catch {
    return res.status(503).json({ detail: 'File storage is unavailable. Keep this page open and try again.' });
  }
}
