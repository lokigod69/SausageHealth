import json

import pytest

from server import intake_ai
from server.db import connect
from test_app import env, client, submit  # Shared fixture creates an isolated database per test.


def test_quotes_and_schema_are_validated():
    sources = {'note': 'Sales reported: PHP 1000. Not verified.'}
    proposed = {'summary': 'A reported daily total.', 'facts': [{'label': 'Reported sales', 'value': 'PHP 1000', 'source_id': 'note', 'quote': 'PHP 1000'}], 'questions': ['Were there any refunds?']}
    assert intake_ai.validate_proposal(json.dumps(proposed), sources)['facts'][0]['value'] == 'PHP 1000'
    proposed['facts'][0]['quote'] = 'PHP 9000'
    with pytest.raises(ValueError):
        intake_ai.validate_proposal(json.dumps(proposed), sources)
    proposed['facts'][0]['quote'] = 'PHP 1000'
    proposed['facts'][0]['source_id'] = 'unseen-file'
    with pytest.raises(ValueError):
        intake_ai.validate_proposal(json.dumps(proposed), sources)
    with pytest.raises(ValueError):
        intake_ai.validate_proposal('{"execute_purchase":true}', sources)


def test_ai_off_without_credentials_never_calls_provider(env, monkeypatch):
    monkeypatch.delenv('SH_AI_ENABLED', raising=False)
    monkeypatch.setattr(intake_ai, 'request_proposal', lambda *args: pytest.fail('Provider must not be called'))
    c = client()
    entry = submit(c).json()
    assert c.post(f"/api/entries/{entry['id']}/extract").status_code == 503
    assert c.get(f"/api/entries/{entry['id']}/draft").json() is None


def test_draft_cache_call_cap_and_no_financial_mutations(env, monkeypatch):
    monkeypatch.setenv('SH_AI_ENABLED', '1')
    monkeypatch.setenv('SH_AI_KEY', 'test-secret-never-a-real-key')
    monkeypatch.setenv('SH_AI_MODEL', 'test/provider-model')
    monkeypatch.setenv('SH_AI_DAILY_CALLS', '1')
    calls = []
    def mock_provider(sources, model, key):
        calls.append(sources)
        return {'summary': 'A reported sales figure.', 'facts': [{'label': 'Reported sales', 'value': 'PHP 1000', 'source_id': 'note', 'quote': 'PHP 1000'}], 'questions': []}
    monkeypatch.setattr(intake_ai, 'request_proposal', mock_provider)
    c = client()
    entry = submit(c).json()
    first = c.post(f"/api/entries/{entry['id']}/extract")
    assert first.status_code == 200
    again = c.post(f"/api/entries/{entry['id']}/extract")
    assert first.json()['id'] == again.json()['id']
    assert len(calls) == 1
    assert c.get('/api/entries').json()[0]['status'] == 'needs_review'
    second = submit(c, '99999999-2222-3333-4444').json()
    assert c.post(f"/api/entries/{second['id']}/extract").status_code == 429
    assert c.get(f"/api/entries/{entry['id']}/draft").json()['status'] == 'complete'
    assert c.get('/api/system').json()['ai'] == 'ready'
    assert client('staff@test.local').post(f"/api/entries/{entry['id']}/extract").status_code == 403


def test_provider_failure_is_redacted_and_original_is_preserved(env, monkeypatch):
    monkeypatch.setenv('SH_AI_ENABLED', '1')
    monkeypatch.setenv('SH_AI_KEY', 'test-secret-never-a-real-key')
    monkeypatch.setenv('SH_AI_MODEL', 'test/provider-model')
    def fail(*args):
        raise RuntimeError('test-secret-never-a-real-key and private financial data')
    monkeypatch.setattr(intake_ai, 'request_proposal', fail)
    c = client()
    entry = submit(c).json()
    response = c.post(f"/api/entries/{entry['id']}/extract")
    assert response.status_code == 502
    assert 'test-secret' not in response.text
    with connect() as db:
        run = dict(db.execute('SELECT * FROM ai_runs').fetchone())
        assert run['status'] == 'failed'
        assert 'test-secret' not in json.dumps(run)
    assert c.get('/api/entries').json()[0]['notes'] == entry['notes']


def test_http_provider_contract_and_validation(monkeypatch):
    import httpx
    real_client = httpx.Client
    def response(request):
        assert str(request.url) == 'https://openrouter.ai/api/v1/chat/completions'
        body = json.loads(request.content)
        assert body['max_tokens'] == 2048 and 'tools' not in body
        assert body['response_format']['type'] == 'json_object'
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps({'summary': 'Draft', 'facts': [], 'questions': []})}}]})
    monkeypatch.setattr(intake_ai.httpx, 'Client', lambda **kwargs: real_client(transport=httpx.MockTransport(response), **kwargs))
    assert intake_ai.request_proposal({'note': 'Hello'}, 'test/model', 'dummy')['summary'] == 'Draft'
