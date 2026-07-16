from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['ok'] is True
    assert r.json()['version'] == '1.8.0'

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
    assert len(data['modules']) == 7
    assert data['modules'][0]['id'] == 'knowledge-library'
    assert data['modules'][-1]['id'] == 'decision-studio'


def test_decision_packet_template():
    r = client.get('/decision-packet/template')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['decision_packet']['packet_version'] == '1.8.0'
    assert 'decision_framing' in data['decision_packet']
    assert 'audit_and_provenance' in data['decision_packet']


def test_decision_packet_analyze():
    r = client.post('/decision-packet/analyze', json={"moduleArtifacts": {"framing": {"decision_question": "Should we proceed?"}}})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert 'catalyst-canvas' in data['legacy_filled_modules']



def test_audit_template():
    r = client.get('/audit/template')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['audit']['audit_version'] == '1.8.0'
    assert 'module_artifact_ledger' in data['audit']


def test_audit_generate_default():
    r = client.post('/audit/generate', json={"inputs": {}, "reviewStatus": "draft"})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['audit']['audit_version'] == '1.8.0'
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
    assert 'catalyst-data' in data['legacy_filled_modules']
    assert data['packet_quality']['source_count'] >= 1


def test_integrated_brief_default():
    r = client.post('/integrated-brief', json={"inputs": {}, "packet": {}})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['version'] == '1.8.0'
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
    assert data['version'] == '1.8.0'
    assert len(data['sections']) >= 8
    assert any(s['id'] == 'finance' for s in data['sections'])


def test_brief_readiness_default():
    r = client.post('/brief-readiness', json={"inputs": {}, "packet": {}})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    readiness = data['readiness']
    assert readiness['readiness_version'] == '1.8.0'
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
    assert data['version'] == '1.8.0'
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
    assert handoff['handoff_version'] == '1.8.0'
    ids = [h['tool_id'] for h in handoff['recommended_handoffs']]
    assert 'economics-forecasting-and-scenario-tool' in ids
    assert any('sc_workbench' in h['shortcode'] for h in handoff['recommended_handoffs'])


def test_integrated_brief_includes_scenario_and_handoff():
    r = client.post('/integrated-brief', json={"inputs": {}, "packet": {}})
    assert r.status_code == 200
    data = r.json()
    assert data['version'] == '1.8.0'
    assert 'scenario_comparison' in data
    assert 'workbench_handoff' in data
    assert 'scenario_comparison_matrix' in data['brief']
    assert 'workbench_handoff_details' in data['brief']



def test_export_center_template():
    r = client.get('/export-center/template')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['export_center']['export_center_version'] == '1.8.0'
    assert any(e['id'] == 'packet_json' for e in data['export_center']['exports'])


def test_decision_packet_save_template():
    r = client.post('/decision-packet/save-template', json={"inputs": {}, "packet": {"project": {"project_name": "Saved packet test"}}, "status": "draft"})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    saved = data['saved_packet']
    assert saved['packet_version'] == '1.8.0'
    assert saved['project_name'] == 'Saved packet test'
    assert 'readiness' in saved
    assert 'integrated_brief' in saved


def test_export_center_bundle_default():
    r = client.post('/export-center/bundle', json={"inputs": {}, "packet": {}})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    bundle = data['export_bundle']
    assert bundle['bundle_version'] == '1.8.0'
    assert 'decision_packet_json' in bundle['exports']
    assert 'integrated_brief_markdown' in bundle['exports']
    assert 'audit_json' in bundle['exports']
    assert 'readiness_json' in bundle['exports']



def test_public_landing_template():
    r = client.get('/public/landing-template')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['version'] == '1.8.0'
    assert data['landing']['page_version'] == '1.8.0'
    assert 'Decision Studio' in data['landing']['headline']
    assert len(data['landing']['workflow']) == 7
    assert data['landing']['workflow'][0]['module'] == 'Knowledge Library'
    assert data['landing']['workflow'][-1]['module'] == 'Decision Studio'


def test_public_demo_template():
    r = client.get('/public/demo-template')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['demo']['demo_version'] == '1.8.0'
    assert len(data['demo']['demo_cards']) >= 4
    assert 'Knowledge Library to source' in data['demo']['public_copy']
    assert 'Decision Studio to decide' in data['demo']['public_copy']


def test_release_manifest_identity():
    response = client.get('/release')
    assert response.status_code == 200
    data = response.json()
    assert data['version'] == '1.8.0'
    assert data['release']['build_fingerprint'] == 'scds-v1.8.0-unified-evidence'
    assert data['release']['decision_packet_schema'] == 'scds-decision-packet/1.1'
    assert data['release']['compatibility']['packet_schema_breaking_changes'] is False


def test_health_reports_cold_start_and_limits():
    response = client.get('/health')
    data = response.json()
    assert response.status_code == 200
    assert data['ready'] is True
    assert data['cold_start_ready'] is True
    assert data['uptime_seconds'] >= 0
    assert data['limits']['max_request_bytes'] == 1048576
    assert response.headers['x-scds-version'] == '1.8.0'


def test_oversized_public_request_is_rejected():
    response = client.post('/analyze', content=b'{' + (b' ' * 1048576) + b'}', headers={'content-type': 'application/json'})
    assert response.status_code == 413
    assert response.json()['error'] == 'request_too_large'


def test_ai_provider_error_uses_deterministic_fallback(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, 'ai_provider_status', lambda: {'configured': True, 'provider': 'gemini', 'model': 'test', 'backend_only': True})
    monkeypatch.setattr(main, 'call_gemini', lambda prompt: (_ for _ in ()).throw(RuntimeError('provider unavailable')))
    response = client.post('/brief', json={'inputs': {}, 'useAI': True})
    assert response.status_code == 200
    brief = response.json()['brief']
    assert brief['ai_used'] is False
    assert brief['source'] == 'deterministic_fallback_after_ai_error'
    assert 'provider unavailable' in brief['ai_error']



def typed_artifact(product, artifact_type, payload, provenance=None):
    return {
        "artifact_schema": "scds-platform-artifact/1.0",
        "artifact_id": f"test-{product}-{artifact_type}",
        "artifact_type": artifact_type,
        "source": {"product": product, "product_version": "test", "artifact_url": "https://example.test/artifact"},
        "provenance": provenance or {"methodology": "Test fixture", "freshness": "current", "confidence": 82, "transformation_history": []},
        "payload": payload,
    }


def test_platform_contract_catalog():
    r = client.get('/integrations/contracts')
    assert r.status_code == 200
    data = r.json()
    assert data['artifact_schema'] == 'scds-platform-artifact/1.0'
    assert data['evidence_schema'] == 'scds-evidence-record/1.0'
    assert [c['product_id'] for c in data['contracts']] == [
        'knowledge-library', 'research-librarian', 'site-intelligence',
        'workbench', 'research-lab', 'platform-core'
    ]


def test_platform_inventory_preserves_legacy_adapters():
    r = client.get('/integrations/platform')
    assert r.status_code == 200
    data = r.json()
    assert data['schema'] == 'scds-platform-artifact/1.0'
    assert any(m['id'] == 'knowledge-library' for m in data['products'])
    assert any(m['id'] == 'catalyst-canvas' for m in data['legacy_modules'])


def test_product_contract_lookup_and_unknown():
    r = client.get('/integrations/contracts/workbench')
    assert r.status_code == 200
    assert 'calculation' in r.json()['contract']['artifact_types']
    missing = client.get('/integrations/contracts/not-a-product')
    assert missing.status_code == 404
    assert missing.json()['error'] == 'unknown_platform_product'


def test_validate_typed_knowledge_library_artifact():
    artifact = typed_artifact('knowledge-library', 'source_record', {
        'title': 'Planetary boundaries evidence',
        'source_type': 'journal article',
        'citation': 'Author (2026) Title. Journal.',
        'quotes': [{'text': 'Evidence excerpt', 'locator': 'p. 4'}],
    })
    r = client.post('/integrations/validate', json={'artifact': artifact, 'strict': True})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['product_id'] == 'knowledge-library'
    assert data['envelope']['provenance']['calculated_integrity_hash'].startswith('sha256:')


def test_validate_rejects_bad_integrity_hash():
    artifact = typed_artifact('knowledge-library', 'source_record', {'title': 'Bad hash'})
    artifact['provenance']['integrity_hash'] = 'sha256:not-the-payload-hash'
    r = client.post('/integrations/validate', json={'artifact': artifact, 'strict': True})
    assert r.status_code == 422
    assert 'integrity hash' in ' '.join(r.json()['errors']).lower()


def test_import_knowledge_library_evidence():
    artifact = typed_artifact('knowledge-library', 'source_record', {
        'title': 'Climate evidence', 'source_type': 'dataset',
        'citation': 'Institution (2026) Climate evidence.',
        'quotes': [{'text': 'Observed change', 'locator': 'Table 2'}],
        'evidence_notes': 'Used for the baseline.',
    })
    r = client.post('/integrations/import', json={'artifact': artifact})
    assert r.status_code == 200
    packet = r.json()['decision_packet']
    assert packet['evidence_registry'][0]['title'] == 'Climate evidence'
    assert packet['citations'][0]['style'] == 'Harvard'
    assert packet['quotations'][0]['locator'] == 'Table 2'
    assert packet['platform_handoffs'][0]['source']['product'] == 'knowledge-library'


def test_import_research_librarian_route():
    artifact = typed_artifact('research-librarian', 'research_route', {
        'query': 'What evidence supports this option?',
        'route': ['Knowledge Library', 'Site Intelligence'],
        'recommended_sources': [{'title': 'Source A', 'reason': 'Baseline'}],
        'evidence_gaps': ['No local implementation data'],
        'follow_up_questions': ['What changes under a stress case?'],
    })
    r = client.post('/decision-packet/import', json={'artifact': artifact})
    assert r.status_code == 200
    packet = r.json()['decision_packet']
    assert packet['research_routes'][0]['query'].startswith('What evidence')
    assert packet['evidence_gaps'] == ['No local implementation data']
    assert packet['follow_up_questions'][0].startswith('What changes')


def test_import_site_intelligence_observation():
    artifact = typed_artifact('site-intelligence', 'indicator_record', {
        'indicator': 'Renewable electricity share', 'geography': 'USA', 'period': '2025',
        'value': 24.2, 'unit': '%', 'source': {'name': 'Public dataset', 'type': 'official'},
        'methodology': 'Reported annual share', 'freshness': '2026-07-01', 'confidence': 90,
    })
    r = client.post('/integrations/import', json={'artifact': artifact})
    assert r.status_code == 200
    packet = r.json()['decision_packet']
    assert packet['live_evidence'][0]['value'] == 24.2
    assert packet['evidence_registry'][0]['source_product'] == 'site-intelligence'


def test_import_workbench_typed_calculation():
    artifact = typed_artifact('workbench', 'calculation', {
        'title': 'Lifecycle NPV', 'formula': '-capex + discounted savings',
        'inputs': {'capex': 100}, 'results': {'npv': 35},
        'assumptions': [{'name': 'Discount rate', 'value': 7, 'sensitivity': 'high'}],
        'validation_checks': [{'status': 'passed'}],
    })
    r = client.post('/integrations/import', json={'artifact': artifact})
    assert r.status_code == 200
    packet = r.json()['decision_packet']
    assert packet['calculation_trace'][0]['calculation'] == 'Lifecycle NPV'
    assert packet['assumptions'][0]['sensitivity'] == 'high'


def test_import_research_lab_experiment():
    artifact = typed_artifact('research-lab', 'experiment', {
        'title': 'Material durability test', 'hypothesis': 'Treatment improves durability',
        'method': {'protocol': 'accelerated aging'}, 'results': {'improvement_percent': 18},
        'validation': {'status': 'replicated'}, 'datasets': [{'id': 'dataset-1'}],
        'limitations': ['Small sample'], 'instruments': ['Chamber A'],
    })
    r = client.post('/integrations/import', json={'artifact': artifact})
    assert r.status_code == 200
    packet = r.json()['decision_packet']
    assert packet['experimental_evidence'][0]['validation']['status'] == 'replicated'
    assert packet['datasets'][0]['id'] == 'dataset-1'


def test_import_platform_core_entity():
    artifact = typed_artifact('platform-core', 'entity_record', {
        'entity': {'id': 'entity-123', 'name': 'Demonstration project'},
        'identifiers': {'internal': 'SC-123'},
        'evidence_ledger': [{'id': 'evidence-1'}],
        'provenance_links': [{'from': 'evidence-1', 'to': 'entity-123'}],
        'relationships': [{'type': 'evaluates', 'target': 'option-a'}],
    })
    r = client.post('/integrations/import', json={'artifact': artifact})
    assert r.status_code == 200
    packet = r.json()['decision_packet']
    assert packet['entities'][0]['id'] == 'entity-123'
    assert packet['evidence_ledger'][0]['id'] == 'evidence-1'


def test_batch_import_builds_cross_product_packet():
    artifacts = [
        typed_artifact('knowledge-library', 'source_record', {'title': 'Evidence source', 'citation': 'Citation'}),
        typed_artifact('research-librarian', 'research_route', {'query': 'Decision question', 'route': ['Evidence source'], 'evidence_gaps': ['Gap']}),
        typed_artifact('site-intelligence', 'indicator_record', {'indicator': 'Indicator', 'value': 12, 'source': {'name': 'Dataset'}}),
        typed_artifact('workbench', 'calculation', {'title': 'Model', 'formula': 'x+y', 'inputs': {'x': 1, 'y': 2}, 'results': 3}),
        typed_artifact('research-lab', 'experiment', {'title': 'Experiment', 'method': {'name': 'test'}, 'results': {'value': 3}}),
        typed_artifact('platform-core', 'entity_record', {'entity': {'id': 'entity-1', 'name': 'Project'}}),
    ]
    r = client.post('/integrations/import-batch', json={'artifacts': artifacts, 'strict': True})
    assert r.status_code == 200
    data = r.json()
    assert data['imported_count'] == 6
    assert data['rejected_count'] == 0
    assert len(data['decision_packet']['platform_handoffs']) == 6
    assert set(data['analysis']['filled_modules']) >= {
        'knowledge-library', 'research-librarian', 'site-intelligence',
        'workbench', 'research-lab', 'platform-core'
    }


def test_platform_handoff_template_has_new_packet_sections():
    r = client.get('/decision-packet/platform-handoffs')
    assert r.status_code == 200
    packet = r.json()['decision_packet']
    assert packet['packet_version'] == '1.8.0'
    assert packet['artifact_schema'] == 'scds-platform-artifact/1.0'
    for key in ['evidence_registry', 'research_routes', 'live_evidence', 'experimental_evidence', 'platform_registry', 'integrity_checks']:
        assert key in packet
