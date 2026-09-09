"""Exercise the actual built image using disposable synthetic data, never a store volume.

Run: python tests/container_smoke.py sausage-health:ci
This checks packaging/persistence; it does not certify real HTTPS or a store phone.
"""
import hashlib
import json
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request


def docker(*args, check=True):
    return subprocess.run(['docker', *args], check=check, capture_output=True, text=True).stdout.strip()


def main(image):
    suffix = secrets.token_hex(6)
    container = 'sh-smoke-' + suffix
    volume = 'sh-smoke-data-' + suffix
    origin = 'https://smoke.example.test'
    password = secrets.token_urlsafe(24)
    docker('volume', 'create', volume)
    try:
        docker('run', '-d', '--name', container, '-p', '127.0.0.1::8080',
               '-v', volume + ':/data', '-e', 'SH_ENV=production', '-e', 'SH_ORIGIN=' + origin,
               '-e', 'SH_AI_ENABLED=0', image)
        base = 'http://' + docker('port', container, '8080/tcp')

        def request(path, body=None, headers=None, expected=200):
            req = urllib.request.Request(base + path, data=body, headers=headers or {})
            try:
                response = urllib.request.urlopen(req, timeout=5)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                data = response.read()
                assert response.status == expected, (path, response.status, data[:200])
                return data, response.headers

        def ready():
            for _ in range(50):
                try:
                    data, _ = request('/api/health')
                    assert json.loads(data)['status'] == 'ok'
                    return
                except (OSError, AssertionError):
                    time.sleep(.2)
            raise AssertionError('Container did not become healthy')

        ready()
        assert b'Sausage Health' in request('/')[0]
        request('/api/entries', expected=401)
        request('/api/export', expected=401)
        request('/api/login', b'{}', {'Content-Type': 'application/json', 'Origin': 'https://wrong.example'}, expected=403)
        assert docker('exec', container, 'id', '-u') == '10001'
        docker('exec', container, 'python', '-c',
               'from server.db import add_user; add_user("smoke@example.test", "Synthetic owner", "owner", ["sausage", "health"], ' + repr(password) + ')')
        auth = {'Origin': origin, 'X-SH-Request': '1', 'Content-Type': 'application/json'}
        _, response_headers = request('/api/login', json.dumps({'email': 'smoke@example.test', 'password': password}).encode(), auth)
        cookie = response_headers['Set-Cookie']
        assert 'Secure' in cookie and 'HttpOnly' in cookie and 'SameSite=strict' in cookie
        assert 'default-src' in response_headers['Content-Security-Policy']
        # Explicit cookie here lets the test inspect a loopback HTTP container;
        # real clients must use the HTTPS proxy before sending a Secure cookie.
        headers = {**auth, 'Cookie': cookie.split(';', 1)[0]}
        boundary = 'smoke-' + suffix
        fields = {'store': 'health', 'category': 'other', 'title': 'SYNTHETIC CONTAINER CHECK',
                  'notes': 'No business facts.', 'occurred_on': '2026-09-09', 'request_key': 'smoke-check-' + suffix}
        parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n' for key, value in fields.items()]
        original = b'SYNTHETIC ORIGINAL ONLY\r\n'
        payload = ''.join(parts).encode() + f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="smoke.txt"\r\nContent-Type: text/plain\r\n\r\n'.encode() + original + f'\r\n--{boundary}--\r\n'.encode()
        upload_headers = {**headers, 'Content-Type': 'multipart/form-data; boundary=' + boundary}
        entry = json.loads(request('/api/entries', payload, upload_headers, 201)[0])
        assert json.loads(request('/api/entries', payload, upload_headers, 201)[0])['id'] == entry['id']
        assert entry['attachments'][0]['sha256'] == hashlib.sha256(original).hexdigest()
        docker('restart', container)
        ready()
        saved = json.loads(request('/api/entries', headers=headers)[0])
        assert len(saved) == 1 and saved[0]['id'] == entry['id']
        assert request('/api/files/' + entry['attachments'][0]['id'], headers=headers)[0] == original
        request('/api/entries/' + entry['id'] + '/review', json.dumps({'status': 'reviewed', 'note': 'Synthetic check', 'version': 1}).encode(), headers)
        docker('exec', container, 'python', '-m', 'server.manage', 'backup', '/data/smoke-backup.zip')
        docker('exec', container, 'python', '-c', 'import zipfile; z=zipfile.ZipFile("/data/smoke-backup.zip"); assert z.testzip() is None; assert "sausagehealth.sqlite" in z.namelist(); assert len([n for n in z.namelist() if n.startswith("uploads/")]) == 1')
        print('Container passed: non-root, bundled UI, production headers, private routes, original upload, idempotency, restart persistence, review and backup.')
    except BaseException:
        print(docker('logs', container, check=False), file=sys.stderr)
        raise
    finally:
        docker('rm', '-f', container, check=False)
        docker('volume', 'rm', volume, check=False)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'sausage-health:ci')
