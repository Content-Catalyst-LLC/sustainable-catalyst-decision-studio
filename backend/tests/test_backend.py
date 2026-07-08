from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['ok'] is True
    assert r.json()['version'] == '1.0.1'

def test_analyze_default():
    r = client.post('/analyze', json={})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert 'scores' in data['results']
    assert data['results']['scores']['weighted'] >= 0


def test_ai_status():
    r = client.get('/ai/status')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert 'configured' in data
    assert data['backend_only'] is True


def test_brief_fallback():
    r = client.post('/brief', json={"inputs": {}, "useAI": False})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert 'brief' in data
    assert data['brief']['ai_used'] is False
    assert 'executive_summary' in data['brief']


def test_report():
    r = client.post('/report', json={"inputs": {}, "includeAI": False})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert 'results' in data
    assert 'brief' in data


def test_templates():
    r = client.get('/templates')
    assert r.status_code == 200
    assert 'scenario_templates' in r.json()
    assert '/brief' in r.json()['ai_endpoints']
