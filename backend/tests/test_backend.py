from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['ok'] is True
    assert r.json()['version'] == '1.12.0'

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
    assert data['decision_packet']['packet_version'] == '1.12.0'
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
    assert data['audit']['audit_version'] == '1.12.0'
    assert 'module_artifact_ledger' in data['audit']


def test_audit_generate_default():
    r = client.post('/audit/generate', json={"inputs": {}, "reviewStatus": "draft"})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['audit']['audit_version'] == '1.12.0'
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
    assert data['version'] == '1.12.0'
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
    assert data['version'] == '1.12.0'
    assert len(data['sections']) >= 8
    assert any(s['id'] == 'finance' for s in data['sections'])


def test_brief_readiness_default():
    r = client.post('/brief-readiness', json={"inputs": {}, "packet": {}})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    readiness = data['readiness']
    assert readiness['readiness_version'] == '1.12.0'
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
    assert data['version'] == '1.12.0'
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
    assert handoff['handoff_version'] == '1.12.0'
    ids = [h['tool_id'] for h in handoff['recommended_handoffs']]
    assert 'economics-forecasting-and-scenario-tool' in ids
    assert any('sc_workbench' in h['shortcode'] for h in handoff['recommended_handoffs'])


def test_integrated_brief_includes_scenario_and_handoff():
    r = client.post('/integrated-brief', json={"inputs": {}, "packet": {}})
    assert r.status_code == 200
    data = r.json()
    assert data['version'] == '1.12.0'
    assert 'scenario_comparison' in data
    assert 'workbench_handoff' in data
    assert 'scenario_comparison_matrix' in data['brief']
    assert 'workbench_handoff_details' in data['brief']



def test_export_center_template():
    r = client.get('/export-center/template')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['export_center']['export_center_version'] == '1.12.0'
    assert any(e['id'] == 'packet_json' for e in data['export_center']['exports'])


def test_decision_packet_save_template():
    r = client.post('/decision-packet/save-template', json={"inputs": {}, "packet": {"project": {"project_name": "Saved packet test"}}, "status": "draft"})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    saved = data['saved_packet']
    assert saved['packet_version'] == '1.12.0'
    assert saved['project_name'] == 'Saved packet test'
    assert 'readiness' in saved
    assert 'integrated_brief' in saved


def test_export_center_bundle_default():
    r = client.post('/export-center/bundle', json={"inputs": {}, "packet": {}})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    bundle = data['export_bundle']
    assert bundle['bundle_version'] == '1.12.0'
    assert 'decision_packet_json' in bundle['exports']
    assert 'integrated_brief_markdown' in bundle['exports']
    assert 'audit_json' in bundle['exports']
    assert 'readiness_json' in bundle['exports']



def test_public_landing_template():
    r = client.get('/public/landing-template')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['version'] == '1.12.0'
    assert data['landing']['page_version'] == '1.12.0'
    assert 'Decision Studio' in data['landing']['headline']
    assert len(data['landing']['workflow']) == 7
    assert data['landing']['workflow'][0]['module'] == 'Knowledge Library'
    assert data['landing']['workflow'][-1]['module'] == 'Decision Studio'


def test_public_demo_template():
    r = client.get('/public/demo-template')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['demo']['demo_version'] == '1.12.0'
    assert len(data['demo']['demo_cards']) >= 4
    assert 'Knowledge Library to source' in data['demo']['public_copy']
    assert 'Decision Studio to decide' in data['demo']['public_copy']


def test_release_manifest_identity():
    response = client.get('/release')
    assert response.status_code == 200
    data = response.json()
    assert data['version'] == '1.12.0'
    assert data['release']['build_fingerprint'] == 'scds-v1.12.0-institutional-domain-decision-packs'
    assert data['release']['decision_packet_schema'] == 'scds-decision-packet/1.5'
    assert data['release']['compatibility']['packet_schema_breaking_changes'] is False


def test_health_reports_cold_start_and_limits():
    response = client.get('/health')
    data = response.json()
    assert response.status_code == 200
    assert data['ready'] is True
    assert data['cold_start_ready'] is True
    assert data['uptime_seconds'] >= 0
    assert data['limits']['max_request_bytes'] == 1048576
    assert response.headers['x-scds-version'] == '1.12.0'


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
    assert packet['packet_version'] == '1.12.0'
    assert packet['artifact_schema'] == 'scds-platform-artifact/1.0'
    for key in ['evidence_registry', 'research_routes', 'live_evidence', 'experimental_evidence', 'platform_registry', 'integrity_checks']:
        assert key in packet



def complete_governance_payload(current='review', requested='approved'):
    return {
        'packet': {},
        'currentState': current,
        'requestedState': requested,
        'actor': 'Review Chair',
        'actorRole': 'review_chair',
        'reason': 'Review completed',
        'decisionOwner': {'name': 'Accountable Owner', 'role': 'Program Director', 'accountable': True},
        'reviewers': [{'reviewer_id': 'reviewer-1', 'name': 'Independent Reviewer', 'role': 'independent_reviewer', 'status': 'approved'}],
        'approvalConditions': [{'condition_id': 'condition-1', 'description': 'Evidence review complete', 'required': True, 'status': 'satisfied'}],
        'exceptions': [],
        'conflictDeclarations': [{'conflict_id': 'conflict-1', 'declared': True, 'description': 'Prior advisory role', 'mitigation': 'Reviewer recused from affected section', 'status': 'recused'}],
        'signoffs': [
            {'signoff_id': 'signoff-owner', 'role': 'decision_owner', 'name': 'Accountable Owner', 'status': 'signed'},
            {'signoff_id': 'signoff-review', 'role': 'independent_reviewer', 'name': 'Independent Reviewer', 'status': 'signed'},
        ],
        'approvalExpiresAt': '2027-07-16',
        'reassessmentDueAt': '2027-01-16',
    }


def test_governance_state_catalog_and_template():
    states = client.get('/governance/states')
    assert states.status_code == 200
    data = states.json()
    assert data['schema'] == 'scds-decision-governance/1.0'
    assert [state['id'] for state in data['states']] == [
        'draft', 'evidence_gathering', 'analysis', 'review', 'revision_required',
        'approved', 'rejected', 'deferred', 'implemented', 'retired'
    ]
    template = client.get('/governance/template').json()['governance']
    assert template['current_state'] == 'draft'
    assert template['export_gate']['professional_reliance_allowed'] is False


def test_governance_blocks_approval_without_human_controls():
    response = client.post('/governance/evaluate', json={
        'currentState': 'review', 'requestedState': 'approved', 'actor': 'Reviewer'
    })
    assert response.status_code == 200
    governance = response.json()['governance']
    assert governance['current_state'] == 'review'
    assert governance['transition_status']['allowed'] is False
    codes = {item['code'] for item in governance['transition_status']['blockers']}
    assert 'missing_decision_owner' in codes
    assert 'missing_owner_signoff' in codes
    assert 'missing_governance_signoff' in codes


def test_governance_approves_complete_human_review():
    response = client.post('/governance/transition', json=complete_governance_payload())
    assert response.status_code == 200
    governance = response.json()['governance']
    assert governance['current_state'] == 'approved'
    assert governance['transition_status']['allowed'] is True
    assert governance['export_gate']['reviewed_export_allowed'] is True
    assert governance['export_gate']['public_export_allowed'] is True
    assert governance['export_gate']['professional_reliance_allowed'] is False
    assert governance['review_history_integrity']['ok'] is True
    assert governance['review_history'][0]['event_hash'].startswith('sha256:')


def test_governance_blocks_open_material_exception():
    payload = complete_governance_payload()
    payload['exceptions'] = [{'exception_id': 'ex-1', 'severity': 'critical', 'description': 'Safety validation incomplete', 'status': 'open'}]
    response = client.post('/decision-packet/governance', json=payload)
    governance = response.json()['governance']
    assert governance['current_state'] == 'review'
    assert any(item['code'] == 'open_material_exception' for item in governance['transition_status']['blockers'])


def test_governance_blocks_unmitigated_conflict():
    payload = complete_governance_payload()
    payload['conflictDeclarations'] = [{'conflict_id': 'c-1', 'declared': True, 'description': 'Financial interest', 'status': 'open'}]
    governance = client.post('/governance/evaluate', json=payload).json()['governance']
    assert governance['current_state'] == 'review'
    assert any(item['code'] == 'unmitigated_conflict' for item in governance['transition_status']['blockers'])


def test_governance_rejects_invalid_transition():
    payload = complete_governance_payload(current='draft', requested='implemented')
    governance = client.post('/governance/transition', json=payload).json()['governance']
    assert governance['current_state'] == 'draft'
    assert any(item['code'] == 'invalid_transition' for item in governance['transition_status']['blockers'])


def test_review_history_detects_tampering():
    first = client.post('/governance/transition', json=complete_governance_payload()).json()['governance']['review_history']
    first[0]['reason'] = 'tampered reason'
    response = client.post('/governance/history/verify', json={'reviewHistory': first})
    integrity = response.json()['integrity']
    assert integrity['ok'] is False
    assert any(item['code'] == 'event_hash_mismatch' for item in integrity['problems'])


def test_governance_is_in_decision_packet_and_export_bundle():
    packet = client.get('/decision-packet/template').json()['decision_packet']
    assert packet['packet_version'] == '1.12.0'
    assert packet['governance_schema'] == 'scds-decision-governance/1.0'
    assert packet['governance_center']['current_state'] == 'draft'
    governance = client.post('/governance/transition', json=complete_governance_payload()).json()['governance']
    response = client.post('/export-center/bundle', json={'inputs': {}, 'packet': {'governance_center': governance}, 'governance': governance})
    bundle = response.json()['export_bundle']
    assert bundle['exports']['governance_json']['current_state'] == 'approved'
    assert bundle['governance_export_gate']['reviewed_export_allowed'] is True



def test_governance_blocks_reviewed_and_public_export_before_approval():
    reviewed = client.post('/export-center/bundle', json={'inputs': {}, 'packet': {}, 'exportAudience': 'reviewed'})
    assert reviewed.status_code == 409
    assert reviewed.json()['error'] == 'governance_export_blocked'
    public = client.post('/decision-packet/export-bundle', json={'inputs': {}, 'packet': {}, 'exportAudience': 'public'})
    assert public.status_code == 409
    assert public.json()['governance_export_gate']['public_export_allowed'] is False


def test_governance_allows_public_export_after_approval():
    governance = client.post('/governance/transition', json=complete_governance_payload()).json()['governance']
    response = client.post('/export-center/bundle', json={'inputs': {}, 'packet': {'governance_center': governance}, 'governance': governance, 'exportAudience': 'public'})
    assert response.status_code == 200
    bundle = response.json()['export_bundle']
    assert bundle['export_audience'] == 'public'
    assert bundle['release_classification'] == 'public'


def test_saved_packet_uses_governance_state():
    governance = client.post('/governance/transition', json=complete_governance_payload()).json()['governance']
    response = client.post('/decision-packet/save-template', json={'inputs': {}, 'packet': {'governance_center': governance}})
    assert response.status_code == 200
    assert response.json()['saved_packet']['status'] == 'approved'



def advanced_scenario_payload():
    return {
        'inputs': {},
        'alternatives': [
            {'id': 'option-a', 'label': 'Option A', 'parameters': {'capex': 800000, 'annualSavings': 190000, 'reductionRate': 30}, 'reversibility': 75, 'stakeholderEquity': 62},
            {'id': 'option-b', 'label': 'Option B', 'parameters': {'capex': 1100000, 'annualSavings': 260000, 'reductionRate': 45}, 'reversibility': 42, 'stakeholderEquity': 76},
            {'id': 'option-c', 'label': 'Option C', 'parameters': {'capex': 600000, 'annualSavings': 100000, 'reductionRate': 18}, 'reversibility': 88, 'stakeholderEquity': 55},
        ],
        'parameterRanges': {
            'capex': {'min': 700000, 'max': 1300000, 'steps': 5},
            'annualSavings': {'min': 90000, 'max': 300000, 'steps': 5},
            'adoptionRate': {'min': 45, 'max': 85, 'steps': 5},
        },
        'sensitivityParameters': ['capex', 'annualSavings', 'adoptionRate'],
        'thresholdTarget': {'parameter': 'annualSavings', 'metric': 'npv', 'operator': '>=', 'value': 0},
        'timeHorizons': [1, 3, 5, 10],
        'gridPoints': 5,
    }


def test_scenario_studio_template():
    response = client.get('/scenario-studio/template')
    assert response.status_code == 200
    template = response.json()['template']
    assert template['schema'] == 'scds-scenario-studio/1.0'
    assert template['alternative_limit'] == 100
    assert 'threshold and break-even search' in template['analyses']
    assert len(template['criteria']) >= 8


def test_scenario_studio_default_analysis():
    response = client.post('/scenario-studio/analyze', json={'inputs': {}})
    assert response.status_code == 200
    data = response.json()
    studio = data['scenario_studio']
    assert data['version'] == '1.12.0'
    assert studio['schema'] == 'scds-scenario-studio/1.0'
    assert studio['alternative_count'] == 5
    assert len(studio['weighted_ranking']) == 5
    assert studio['recommended_alternative_id']
    assert len(studio['uncertainty_envelopes']) == 5


def test_scenario_studio_supports_custom_alternatives_and_weighted_unweighted_rankings():
    payload = advanced_scenario_payload()
    payload['criteria'] = [
        {'id': 'financial_value', 'label': 'Financial value', 'metric': 'npv', 'weight': 80},
        {'id': 'reversibility', 'label': 'Reversibility', 'metric': 'reversibility', 'weight': 20},
    ]
    studio = client.post('/scenario-studio/analyze', json=payload).json()['scenario_studio']
    assert studio['alternative_count'] == 3
    assert len(studio['weighted_ranking']) == 3
    assert len(studio['unweighted_ranking']) == 3
    assert studio['alternatives'][0]['criteria'][0]['weight'] == 80


def test_scenario_studio_one_way_sensitivity_and_tornado_ranking():
    data = client.post('/scenario-studio/sensitivity', json=advanced_scenario_payload()).json()
    sensitivity = data['sensitivity_analysis']
    assert len(sensitivity['parameters']) == 3
    assert len(sensitivity['tornado_ranking']) == 3
    assert any(item['most_sensitive'] for item in sensitivity['parameters'])
    assert all(len(item['observations']) == 5 for item in sensitivity['parameters'])


def test_scenario_studio_multi_variable_grid():
    studio = client.post('/scenario-studio/analyze', json=advanced_scenario_payload()).json()['scenario_studio']
    grid = studio['multi_variable_sensitivity']
    assert grid['parameters'] == ['capex', 'annualSavings']
    assert len(grid['grid']) == 9
    assert all('decision_score' in row for row in grid['grid'])


def test_scenario_studio_threshold_break_even_search():
    data = client.post('/scenario-studio/threshold', json=advanced_scenario_payload()).json()
    threshold = data['threshold_analysis']
    assert threshold['parameter'] == 'annualSavings'
    assert threshold['metric'] == 'npv'
    assert threshold['screening_resolution'] == 25
    assert isinstance(threshold['observations'], list)
    assert all('target_met' in item for item in threshold['observations'])


def test_scenario_studio_stakeholder_distribution_and_option_value():
    payload = advanced_scenario_payload()
    payload['alternatives'][0]['stakeholder_impacts'] = [
        {'stakeholder': 'Workers', 'impact_score': 80, 'weight': 2},
        {'stakeholder': 'Residents', 'impact_score': 40, 'weight': 1},
    ]
    studio = client.post('/scenario-studio/analyze', json=payload).json()['scenario_studio']
    distribution = studio['stakeholder_distribution'][0]
    assert distribution['minimum_group_score'] == 40
    assert distribution['maximum_group_score'] == 80
    assert len(studio['reversibility_option_value']) == 3
    assert all('option_value' in item for item in studio['reversibility_option_value'])


def test_scenario_studio_time_horizon_comparison():
    studio = client.post('/scenario-studio/analyze', json=advanced_scenario_payload()).json()['scenario_studio']
    horizons = studio['time_horizon_comparison']
    assert [item['years'] for item in horizons] == [1, 3, 5, 10]
    assert all('npv' in item and 'total_avoided_tco2e' in item for item in horizons)


def test_scenario_studio_updates_decision_packet():
    response = client.post('/decision-packet/scenario-studio', json=advanced_scenario_payload())
    packet = response.json()['decision_packet']
    assert packet['packet_version'] == '1.12.0'
    assert packet['scenario_studio_schema'] == 'scds-scenario-studio/1.0'
    assert packet['scenario_studio']['alternative_count'] == 3
    assert packet['sensitivity_analysis']['parameters']
    assert 'threshold_analysis' in packet
    assert 'uncertainty_analysis' in packet


def test_scenario_studio_is_saved_and_exported():
    studio = client.post('/scenario-studio/analyze', json=advanced_scenario_payload()).json()['scenario_studio']
    saved = client.post('/decision-packet/save-template', json={'inputs': {}, 'packet': {'scenario_studio': studio}, 'scenarioStudio': studio}).json()['saved_packet']
    assert saved['scenario_studio']['schema'] == 'scds-scenario-studio/1.0'
    bundle = client.post('/export-center/bundle', json={'inputs': {}, 'packet': {'scenario_studio': studio}, 'scenarioStudio': studio}).json()['export_bundle']
    assert bundle['exports']['scenario_studio_json']['alternative_count'] == 3
    assert any(item['id'] == 'scenario_studio_json' for item in bundle['export_manifest'])


def test_health_and_release_publish_scenario_studio_schema():
    health = client.get('/health').json()
    release = client.get('/release').json()['release']
    assert health['scenario_studio_schema'] == 'scds-scenario-studio/1.0'
    assert release['scenario_studio_schema'] == 'scds-scenario-studio/1.0'
    assert release['compatibility']['advanced_scenario_studio'] is True



def test_collaboration_template_and_roles():
    response = client.get('/collaboration/template')
    assert response.status_code == 200
    data = response.json()
    assert data['room']['schema'] == 'scds-collaborative-decision-room/1.0'
    assert data['room']['canonical_persistence'] == 'wordpress'
    roles = {item['id']: item['permissions'] for item in data['roles']['roles']}
    assert 'manage_room' in roles['owner']
    assert roles['observer'] == []


def room_payload(action='create', room=None, packet=None, payload=None, role='owner'):
    return {
        'packet': packet or {},
        'room': room or {},
        'action': action,
        'actor': 'Tariq Ahmad',
        'actorRole': role,
        'targetType': 'decision_packet',
        'targetId': 'packet-root',
        'payload': payload or {},
        'reason': 'Collaboration regression test',
    }


def test_collaboration_room_comment_and_notifications():
    created = client.post('/collaboration/room', json=room_payload()).json()
    room = created['room']
    room['members'].append({'member_id': 'member-reviewer', 'name': 'Reviewer', 'email': 'reviewer@example.org', 'role': 'reviewer', 'status': 'active'})
    response = client.post('/collaboration/comment', json=room_payload(room=room, packet=created['decision_packet'], payload={'content': 'Please verify the financial assumptions.'}, role='owner'))
    assert response.status_code == 200
    data = response.json()
    assert data['comment']['target_type'] == 'decision_packet'
    assert data['room']['metrics']['open_comment_count'] == 1
    assert data['room']['notifications'][0]['recipient'] == 'reviewer@example.org'
    assert data['room']['activity_integrity']['ok'] is True


def test_collaboration_change_request_resolution_and_revision_diff():
    created = client.post('/collaboration/room', json=room_payload()).json()
    request = client.post('/collaboration/change-request', json=room_payload(room=created['room'], packet=created['decision_packet'], payload={'title': 'Update decision question', 'description': 'Clarify the decision frame.', 'packet_patch': {'project': {'decision_question': 'Should the phased option proceed?'}}})).json()
    change = request['change_request']
    resolved = client.post('/collaboration/action', json=room_payload(action='resolve_change_request', room=request['room'], packet=request['decision_packet'], payload={'change_request_id': change['change_request_id'], 'status': 'implemented', 'resolution': 'Accepted after review.'}, role='owner'))
    assert resolved.status_code == 200
    data = resolved.json()
    assert data['change_request']['status'] == 'implemented'
    assert data['decision_packet']['project']['decision_question'] == 'Should the phased option proceed?'
    assert data['comparison']['change_count'] >= 1
    assert 'project.decision_question' in data['comparison']['changed_paths']


def test_collaboration_snapshots_compare_and_hash_chain_tamper_detection():
    created = client.post('/collaboration/room', json=room_payload()).json()
    first = client.post('/collaboration/snapshot', json=room_payload(room=created['room'], packet=created['decision_packet'], payload={'label': 'First'})).json()
    packet = first['decision_packet']
    packet['project']['project_name'] = 'Updated project'
    second = client.post('/collaboration/snapshot', json=room_payload(room=first['room'], packet=packet, payload={'label': 'Second'})).json()
    compared = client.post('/collaboration/action', json=room_payload(action='compare_snapshots', room=second['room'], packet=second['decision_packet'])).json()
    assert compared['comparison']['change_count'] >= 1
    assert 'project.project_name' in compared['comparison']['changed_paths']
    history = compared['room']['activity_timeline']
    history[0]['details'] = {'tampered': True}
    verify = client.post('/collaboration/action', json=room_payload(action='evaluate', room={**compared['room'], 'activity_timeline': history}, packet=compared['decision_packet'])).json()
    assert verify['room']['activity_integrity']['ok'] is False


def test_private_room_share_grant_hashes_token_and_exposes_once():
    created = client.post('/collaboration/room', json=room_payload()).json()
    response = client.post('/collaboration/share', json=room_payload(room=created['room'], packet=created['decision_packet'], payload={'member': {'name': 'Client Reviewer', 'email': 'client@example.org', 'role': 'client'}}))
    assert response.status_code == 200
    data = response.json()
    assert data['share_token_once']
    assert data['share_grant']['token_hash'].startswith('sha256:')
    assert data['share_token_once'] not in str(data['room'])
    assert data['room']['visibility'] == 'private'


def test_locked_approved_version_blocks_revision_until_reopened():
    governance = client.post('/governance/transition', json=complete_governance_payload()).json()['governance']
    created = client.post('/collaboration/room', json=room_payload(packet={'governance_center': governance})).json()
    locked = client.post('/collaboration/action', json=room_payload(action='lock_version', room=created['room'], packet=created['decision_packet'], payload={'label': 'Approved version'}, role='owner'))
    assert locked.status_code == 200
    locked_data = locked.json()
    assert locked_data['room']['locked_version']['locked'] is True
    revision = client.post('/collaboration/action', json=room_payload(action='apply_revision', room=locked_data['room'], packet=locked_data['decision_packet'], payload={'packet_patch': {'project': {'project_name': 'Unauthorized change'}}}, role='editor'))
    assert revision.status_code == 409
    assert revision.json()['error'] == 'approved_version_locked'
    reopened = client.post('/collaboration/action', json=room_payload(action='reopen_version', room=locked_data['room'], packet=locked_data['decision_packet'], role='owner') | {'reason': 'Material evidence changed.'})
    assert reopened.status_code == 200
    assert reopened.json()['room']['locked_version']['locked'] is False


def test_collaboration_contact_and_engagement_handoff():
    created = client.post('/collaboration/room', json=room_payload()).json()
    response = client.post('/collaboration/contact-handoff', json=room_payload(room=created['room'], packet=created['decision_packet'], payload={'collaboration_needs': ['private document review', 'client approval'], 'requested_next_action': 'Create a secure engagement workspace.'}))
    assert response.status_code == 200
    handoff = response.json()['contact_engagement_handoff']
    assert handoff['schema'] == 'sc-contact-engagement-handoff/1.0'
    assert handoff['private_workspace_required'] is True
    assert handoff['source_version'] == '1.12.0'


def test_collaboration_is_saved_and_exported_with_packet_schema_1_5():
    created = client.post('/collaboration/room', json=room_payload()).json()
    room = created['room']
    saved = client.post('/decision-packet/save-template', json={'inputs': {}, 'packet': created['decision_packet'], 'collaboration': room}).json()['saved_packet']
    assert saved['decision_packet']['packet_version'] == '1.12.0'
    assert saved['decision_packet']['collaboration_room_schema'] == 'scds-collaborative-decision-room/1.0'
    assert saved['collaboration']['room_id'] == room['room_id']
    bundle = client.post('/export-center/bundle', json={'inputs': {}, 'packet': created['decision_packet'], 'collaboration': room}).json()['export_bundle']
    assert bundle['exports']['collaboration_json']['room_id'] == room['room_id']
    assert any(item['id'] == 'collaboration_json' for item in bundle['export_manifest'])


def test_collaboration_permission_denies_observer_comment():
    created = client.post('/collaboration/room', json=room_payload()).json()
    response = client.post('/collaboration/comment', json=room_payload(room=created['room'], packet=created['decision_packet'], payload={'content': 'Observer should not write.'}, role='observer'))
    assert response.status_code == 403
    assert response.json()['error'] == 'collaboration_permission_denied'


def test_health_and_release_publish_collaboration_schemas():
    health = client.get('/health').json()
    release = client.get('/release').json()['release']
    assert health['collaboration_room_schema'] == 'scds-collaborative-decision-room/1.0'
    assert health['collaboration_event_schema'] == 'scds-collaboration-event/1.0'
    assert release['collaboration_room_schema'] == 'scds-collaborative-decision-room/1.0'
    assert release['compatibility']['collaborative_decision_rooms'] is True


def complete_pack_payload(pack_id='climate-energy-strategy'):
    catalog = client.get('/decision-packs/catalog').json()['packs']
    pack = next(item for item in catalog if item['id'] == pack_id)
    return {
        'packId': pack_id,
        'organizationProfile': {field: f'value-{field}' for field in pack['required_intake_fields']},
        'selectedEvidence': pack['required_evidence'],
        'reviewerAssignments': [{'role': role, 'name': role.replace('_', ' ').title()} for role in pack['review_roles']],
        'actor': 'Tariq Ahmad',
        'notes': 'Institutional pack regression test',
    }

def test_decision_pack_catalog_has_ten_institutional_domains():
    response = client.get('/decision-packs/catalog')
    assert response.status_code == 200
    data = response.json()
    assert data['schema'] == 'scds-institutional-decision-pack/1.0'
    assert data['count'] == 10
    ids = {item['id'] for item in data['packs']}
    assert 'responsible-ai-governance' in ids
    assert 'humanitarian-development-program' in ids
    assert 'advisory-diagnostic-recommendation' in ids

def test_decision_pack_detail_and_alias_lookup():
    direct = client.get('/decision-packs/responsible-ai-governance')
    alias = client.get('/decision-packs/ai')
    assert direct.status_code == 200
    assert alias.status_code == 200
    assert alias.json()['pack']['id'] == 'responsible-ai-governance'
    assert direct.json()['pack']['governance_defaults']['ai_approval_allowed'] is False

def test_decision_pack_validation_identifies_missing_evidence_and_roles():
    response = client.post('/decision-packs/validate', json={'packId': 'urban-resilience'})
    assert response.status_code == 200
    validation = response.json()['validation']
    assert validation['readiness_percent'] == 0
    assert validation['professional_reliance_allowed'] is False
    assert any(item['code'] == 'missing_evidence' for item in validation['blockers'])
    assert any(item['code'] == 'missing_review_role' for item in validation['blockers'])

def test_complete_decision_pack_validation_is_governance_ready():
    response = client.post('/decision-packs/validate', json=complete_pack_payload())
    assert response.status_code == 200
    validation = response.json()['validation']
    assert validation['readiness_percent'] == 100
    assert validation['ready_for_governance_review'] is True
    assert validation['blockers'] == []

def test_apply_decision_pack_updates_packet_schema_and_plans():
    response = client.post('/decision-packs/apply', json=complete_pack_payload('responsible-ai-governance'))
    assert response.status_code == 200
    data = response.json()
    packet = data['decision_packet']
    assert data['schema'] == 'scds-decision-pack-application/1.0'
    assert packet['packet_version'] == '1.12.0'
    assert packet['decision_pack_schema'] == 'scds-institutional-decision-pack/1.0'
    assert packet['institutional_decision_pack']['pack_id'] == 'responsible-ai-governance'
    assert len(packet['criteria_registry']) == 6
    assert packet['model_plan'][0]['execution_authority'] == 'workbench'
    assert packet['governance_center']['domain_pack_requirements']['ai_approval_allowed'] is False

def test_domain_pack_packet_endpoint_preserves_existing_packet_content():
    payload = complete_pack_payload('organizational-policy')
    payload['selectedEvidence'] = [item for item in payload['selectedEvidence'] if item != 'problem_definition']
    payload['packet'] = {'project': {'project_name': 'Policy review'}, 'evidence_registry': [{'evidence_type': 'problem_definition'}]}
    response = client.post('/decision-packet/domain-pack', json=payload)
    packet = response.json()['decision_packet']
    assert packet['project']['project_name'] == 'Policy review'
    assert packet['institutional_decision_pack']['pack_id'] == 'organizational-policy'
    status = {item['id']: item['status'] for item in packet['evidence_plan']}
    assert status['problem_definition'] == 'decision_packet'

def test_unknown_decision_pack_returns_404():
    response = client.post('/decision-packs/apply', json={'packId': 'not-a-pack'})
    assert response.status_code == 404
    assert response.json()['error'] == 'unknown_decision_pack'

def test_decision_pack_is_saved_and_exported():
    applied = client.post('/decision-packs/apply', json=complete_pack_payload('sustainable-procurement')).json()
    pack = applied['decision_pack']
    packet = applied['decision_packet']
    saved = client.post('/decision-packet/save-template', json={'inputs': {}, 'packet': packet, 'decisionPack': pack}).json()['saved_packet']
    assert saved['decision_pack']['pack_id'] == 'sustainable-procurement'
    bundle = client.post('/export-center/bundle', json={'inputs': {}, 'packet': packet, 'decisionPack': pack}).json()['export_bundle']
    assert bundle['exports']['decision_pack_json']['pack_id'] == 'sustainable-procurement'
    assert any(item['id'] == 'decision_pack_json' for item in bundle['export_manifest'])

def test_health_and_release_publish_decision_pack_schemas():
    health = client.get('/health').json()
    release = client.get('/release').json()['release']
    assert health['decision_pack_schema'] == 'scds-institutional-decision-pack/1.0'
    assert health['decision_pack_application_schema'] == 'scds-decision-pack-application/1.0'
    assert release['decision_pack_schema'] == 'scds-institutional-decision-pack/1.0'
    assert release['compatibility']['institutional_domain_decision_packs'] is True
    assert release['compatibility']['regulated_assurance_prohibited'] is True
