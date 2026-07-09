from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['ok'] is True
    assert r.json()['version'] == '1.7.0'

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
    assert data['decision_packet']['packet_version'] == '1.7.0'
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
    assert data['audit']['audit_version'] == '1.7.0'
    assert 'module_artifact_ledger' in data['audit']


def test_audit_generate_default():
    r = client.post('/audit/generate', json={"inputs": {}, "reviewStatus": "draft"})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['audit']['audit_version'] == '1.7.0'
    assert data['audit_summary']['assumptions_count'] >= 5
    assert data['audit_summary']['calculation_trace_count'] >= 4


def test_artifact_adapters_catalog():
    r = client.get('/integrations/adapters')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    ids = [a['module_id'] for a in data['adapters']]
    assert 'catalyst-canvas' in ids
    assert 'catalyst-finance' in ids
    assert 'workbench' in ids


def test_import_canvas_artifact():
    artifact = {
        "challenge": "How should the project be framed?",
        "audience": "Decision reviewer",
        "goal": "Create a traceable decision packet",
        "constraint": "Use only reviewed sources",
        "point_of_view": "A reviewer needs a clear decision frame.",
        "how_might_we": ["How might we make the decision auditable?"],
        "prototype": {"title": "Decision Packet"},
        "test_plan": {"signal": "Reviewer can identify gaps"}
    }
    r = client.post('/integrations/import', json={"artifact": artifact, "moduleId": "catalyst-canvas"})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['import_result']['summary']['module_id'] == 'catalyst-canvas'
    assert data['decision_packet']['decision_framing']['challenge'] == artifact['challenge']


def test_import_finance_artifact():
    artifact = {
        "project": {"name": "Efficiency retrofit", "category": "Energy"},
        "inputs": {"capital_cost": 250000, "annual_savings": 52000},
        "results": {"npv": 167572.47, "roi_percent": 144.29, "payback_years": 4.09, "benefit_cost_ratio": 1.8},
        "interpretation": {"risk_level": "Moderate concern", "flags": []}
    }
    r = client.post('/decision-packet/import', json={"artifact": artifact, "moduleId": "catalyst-finance"})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['decision_packet']['financial_tradeoffs']['results']['npv'] == 167572.47
    assert data['analysis']['packet_quality']['calculation_trace_count'] >= 1


def test_decision_packet_analyze_normalizes_artifacts():
    artifact = {"entity": {"name": "Project", "type": "initiative"}, "indicator": {"name": "Data completeness", "unit": "score", "direction": "higher"}, "period": "2026-Q2", "values": {"baseline": 62, "current": 78}, "source": {"name": "Tracker", "type": "internal"}, "confidence": 72, "review_status": "needs_review"}
    r = client.post('/decision-packet/analyze', json={"moduleArtifacts": {"catalyst-data": artifact}})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert 'catalyst-data' in data['filled_modules']
    assert data['packet_quality']['source_count'] >= 1


def test_integrated_brief_default():
    r = client.post('/integrated-brief', json={"inputs": {}, "packet": {}})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['version'] == '1.7.0'
    assert 'brief' in data
    assert 'executive_summary' in data['brief']
    assert 'exports' in data
    assert 'markdown' in data['exports']


def test_decision_packet_brief_with_canvas_artifact():
    packet = {
        "decision_framing": {
            "challenge": "How should the integrated platform decision be framed?",
            "decision_question": "Should the platform proceed to public demo?"
        },
        "sources": [{"source_title": "Demo source", "confidence": 80, "used_for": "brief test"}]
    }
    r = client.post('/decision-packet/brief', json={"inputs": {}, "packet": packet})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['brief']['decision_question'] == "Should the platform proceed to public demo?"
    assert data['brief']['brief_readiness']['readiness_percent'] >= 0


def test_review_status_template():
    r = client.get('/review/status-template')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['version'] == '1.7.0'
    assert len(data['sections']) >= 8
    assert any(s['id'] == 'finance' for s in data['sections'])


def test_brief_readiness_default():
    r = client.post('/brief-readiness', json={"inputs": {}, "packet": {}})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    readiness = data['readiness']
    assert readiness['readiness_version'] == '1.7.0'
    assert 0 <= readiness['readiness_percent'] <= 100
    assert 'sections' in readiness
    assert 'export_gate' in readiness
    assert readiness['export_gate']['professional_reliance_allowed'] is False


def test_decision_packet_readiness_with_sources():
    packet = {
        "decision_framing": {"decision_question": "Should the project proceed?"},
        "sources": [{"source_title": "Measurement record", "confidence": 85, "used_for": "readiness test"}],
        "impact_measurement": {"records": [{"initiative": "Project", "indicator": "Impact", "baseline_value": 1, "current_value": 2, "target_value": 3}]},
        "claim_and_risk_review": {"records": [{"claim": "Impact is improving", "risk_level": "Medium"}]},
        "financial_tradeoffs": {"results": {"npv": 1000, "roi_percent": 12, "payback_years": 3}},
        "assumptions": [{"assumption": "Savings", "value": 100, "review_status": "needs review"}],
        "calculation_trace": [{"calculation": "NPV", "result": 1000}],
    }
    r = client.post('/decision-packet/readiness', json={"inputs": {}, "packet": packet})
    assert r.status_code == 200
    data = r.json()
    readiness = data['readiness']
    assert readiness['readiness_percent'] > 50
    assert readiness['counts']['sources'] >= 1
    assert any(s['id'] == 'evidence' for s in readiness['sections'])



def test_scenario_comparison_default():
    r = client.post('/scenario-comparison', json={"inputs": {}, "packet": {}})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['version'] == '1.7.0'
    comparison = data['scenario_comparison']
    assert comparison['scenario_count'] >= 4
    assert 'matrix' in comparison
    assert 'recommended_option' in comparison
    assert comparison['matrix'][0]['label'] == 'Baseline'


def test_decision_packet_scenario_comparison_with_imported_options():
    packet = {
        "scenarios": {
            "records": [
                {"label": "Option A", "annual_avoided_tco2e": 100, "npv": 5000, "payback_years": 4, "risk_score": 50, "confidence": 70},
                {"label": "Option B", "annual_avoided_tco2e": 300, "npv": 12000, "payback_years": 3, "risk_score": 42, "confidence": 82},
            ]
        }
    }
    r = client.post('/decision-packet/scenario-comparison', json={"inputs": {}, "packet": packet})
    assert r.status_code == 200
    data = r.json()
    assert data['scenario_comparison']['scenario_count'] == 2
    assert data['scenario_comparison']['recommended_option'] in ['Option A', 'Option B']
    assert data['scenario_comparison']['matrix'][1]['delta_vs_baseline']['annual_avoided_tco2e'] == 200


def test_workbench_handoff_default():
    r = client.post('/workbench/handoff', json={"inputs": {}, "packet": {}})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    handoff = data['workbench_handoff']
    assert handoff['handoff_version'] == '1.7.0'
    ids = [h['tool_id'] for h in handoff['recommended_handoffs']]
    assert 'economics-forecasting-and-scenario-tool' in ids
    assert any('sc_workbench' in h['shortcode'] for h in handoff['recommended_handoffs'])


def test_integrated_brief_includes_scenario_and_handoff():
    r = client.post('/integrated-brief', json={"inputs": {}, "packet": {}})
    assert r.status_code == 200
    data = r.json()
    assert data['version'] == '1.7.0'
    assert 'scenario_comparison' in data
    assert 'workbench_handoff' in data
    assert 'scenario_comparison_matrix' in data['brief']
    assert 'workbench_handoff_details' in data['brief']



def test_export_center_template():
    r = client.get('/export-center/template')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['export_center']['export_center_version'] == '1.7.0'
    assert any(e['id'] == 'packet_json' for e in data['export_center']['exports'])


def test_decision_packet_save_template():
    r = client.post('/decision-packet/save-template', json={"inputs": {}, "packet": {"project": {"project_name": "Saved packet test"}}, "status": "draft"})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    saved = data['saved_packet']
    assert saved['packet_version'] == '1.7.0'
    assert saved['project_name'] == 'Saved packet test'
    assert 'readiness' in saved
    assert 'integrated_brief' in saved


def test_export_center_bundle_default():
    r = client.post('/export-center/bundle', json={"inputs": {}, "packet": {}})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    bundle = data['export_bundle']
    assert bundle['bundle_version'] == '1.7.0'
    assert 'decision_packet_json' in bundle['exports']
    assert 'integrated_brief_markdown' in bundle['exports']
    assert 'audit_json' in bundle['exports']
    assert 'readiness_json' in bundle['exports']



def test_public_landing_template():
    r = client.get('/public/landing-template')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['version'] == '1.7.0'
    assert data['landing']['page_version'] == '1.7.0'
    assert 'Decision Studio' in data['landing']['headline']
    assert len(data['landing']['workflow']) == 8


def test_public_demo_template():
    r = client.get('/public/demo-template')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['demo']['demo_version'] == '1.7.0'
    assert len(data['demo']['demo_cards']) >= 4
    assert 'Decision Studio to decide' in data['demo']['public_copy']
