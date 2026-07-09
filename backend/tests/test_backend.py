from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['ok'] is True
    assert r.json()['version'] == '1.1.1'

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


def test_integrations_modules():
    r = client.get('/integrations/modules')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert len(data['modules']) == 8
    assert data['modules'][0]['id'] == 'catalyst-canvas'
    assert data['modules'][-1]['id'] == 'decision-studio'


def test_decision_packet_template():
    r = client.get('/decision-packet/template')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['decision_packet']['packet_version'] == '1.1.1'
    assert 'decision_framing' in data['decision_packet']
    assert 'audit_and_provenance' in data['decision_packet']


def test_decision_packet_analyze():
    r = client.post('/decision-packet/analyze', json={"moduleArtifacts": {"framing": {"decision_question": "Should we proceed?"}}})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['workflow_readiness_percent'] > 0
    assert 'catalyst-canvas' in data['filled_modules']



def test_audit_template():
    r = client.get('/audit/template')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['audit']['audit_version'] == '1.1.1'
    assert 'module_artifact_ledger' in data['audit']


def test_audit_generate_default():
    r = client.post('/audit/generate', json={"inputs": {}, "reviewStatus": "draft"})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['audit']['audit_version'] == '1.1.1'
    assert data['audit_summary']['assumptions_count'] >= 5
    assert data['audit_summary']['calculation_trace_count'] >= 4
