from __future__ import annotations

import json
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.domains.narrative_risk import NARRATIVE_RISK_DOMAIN_SCHEMA
from app.persistence.database import EXPECTED_SCHEMA_REVISION, engine_for_url
from app.persistence.models import Artifact, Claim, DecisionEvent, DecisionModule, DecisionObject, EvidenceLink
from app.persistence.seed import seed_module_registry

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


def _db(monkeypatch, tmp_path):
    db = tmp_path / 'v370.sqlite3'
    url = f'sqlite:///{db}'
    cfg = Config(str(ROOT / 'backend/alembic.ini'))
    cfg.set_main_option('script_location', str(ROOT / 'backend/migrations'))
    cfg.set_main_option('sqlalchemy.url', url)
    command.upgrade(cfg, 'head')
    monkeypatch.setenv('SCDS_DATABASE_URL', url)
    monkeypatch.setenv('SCDS_PERSISTENCE_REQUIRED', 'true')
    monkeypatch.setenv('SCDS_PERSISTENCE_WRITE_ENABLED', 'true')
    monkeypatch.setenv('SCDS_REPOSITORY_API_KEY', 'test-repository-key')
    seed_module_registry()
    return url


def _headers():
    return {'x-scds-api-key': 'test-repository-key'}


def _decision(monkeypatch, tmp_path, decision_id='dec-v370'):
    url = _db(monkeypatch, tmp_path)
    project = client.post('/repository/projects', headers=_headers(), json={
        'project_id': 'proj-v370', 'title': 'Narrative Risk Migration Test'
    })
    assert project.status_code == 200, project.text
    decision = client.post('/repository/decisions', headers=_headers(), json={
        'decision_id': decision_id,
        'project_id': 'proj-v370',
        'decision_question': 'Which emerging risks need governed review?'
    })
    assert decision.status_code == 200, decision.text
    return url


def test_v370_narrative_risk_contract_and_release_boundary():
    health = client.get('/health').json()
    assert health['version'] == '3.14.0'
    assert health['narrative_risk_domain_schema'] == NARRATIVE_RISK_DOMAIN_SCHEMA
    release = client.get('/release').json()['release']
    assert release['release_name'] == 'Global Authentication & Authorization Integration'
    assert release['build_fingerprint'] == 'scds-v3.14.0-global-authentication-authorization-integration'
    assert release['backend_architecture']['database_migration'] is False
    assert release['backend_architecture']['narrative_risk_python_domain_migration'] is False
    assert release['backend_architecture']['global_impact_python_domain_migration'] is False
    assert release['backend_architecture']['finance_python_domain_migration'] is False
    assert release['narrative_risk']['status'] == 'python-domain-authoritative'
    assert release['narrative_risk']['automatic_truth_verification'] is False
    assert release['narrative_risk']['automatic_causality_inference'] is False
    assert release['narrative_risk']['final_decision_authority'] == 'human-governed'
    contract = client.get('/narrative-risk/contract').json()['narrative_risk_contract']
    assert contract['schema'] == NARRATIVE_RISK_DOMAIN_SCHEMA
    assert contract['storage_authority'] == 'python-postgresql'
    assert contract['boundaries']['claim_is_not_fact_without_evidence'] is True
    assert contract['boundaries']['signal_is_not_causality'] is True
    assert contract['boundaries']['automatic_truth_verification'] is False


def test_v370_narrative_risk_requires_scoped_auth(monkeypatch):
    monkeypatch.setenv('SCDS_REPOSITORY_API_KEY', 'test-repository-key')
    read = client.get('/narrative-risk/decisions/example')
    assert read.status_code == 403
    assert read.json()['required_scope'] == 'narrative-risk:read'
    write = client.put('/narrative-risk/decisions/example', json={})
    assert write.status_code == 403
    assert write.json()['required_scope'] == 'narrative-risk:write'


def test_v370_narrative_risk_normalizes_claims_signals_and_evidence(monkeypatch, tmp_path):
    url = _decision(monkeypatch, tmp_path)
    payload = {
        'risk_context': {'scope': 'market-and-governance'},
        'actors': [{'id': 'actor-1', 'name': 'Operator'}],
        'exposures': [{'id': 'exp-1', 'type': 'reputational'}],
        'narratives': [{'id': 'n-1', 'label': 'Supply disruption narrative'}],
        'mitigations': [{'id': 'm-1', 'action': 'Diversify suppliers'}],
        'watch_conditions': [{'id': 'w-1', 'condition': 'Supplier outage exceeds 48h'}],
        'claims': [
            {'id': 'claim-1', 'text': 'Supplier concentration may increase disruption exposure.', 'epistemic_status': 'unresolved', 'kind': 'risk-hypothesis'},
            {'id': 'claim-2', 'text': 'A competitor is amplifying the disruption narrative.', 'epistemic_status': 'contested', 'kind': 'claim'},
        ],
        'signals': [
            {'id': 'signal-1', 'label': 'Supplier outage report', 'signal_type': 'operational', 'severity': 'high', 'source_ref': 'site-intelligence:signal:1'}
        ],
        'evidence_links': [
            {'id': 'link-1', 'claim_id': 'claim-1', 'evidence_ref': 'library:evidence:1', 'relation': 'supports'},
            {'id': 'link-2', 'claim_id': 'claim-2', 'evidence_ref': 'library:evidence:2', 'relation': 'challenges'},
        ],
        'provenance': {'source': 'test'},
        'provenance_ref': 'prov:narrative-risk-test',
    }
    response = client.put('/narrative-risk/decisions/dec-v370', headers=_headers(), json=payload)
    assert response.status_code == 200, response.text
    state = response.json()['narrative_risk']
    assert state['schema'] == NARRATIVE_RISK_DOMAIN_SCHEMA
    assert len(state['claims']) == 2
    assert len(state['signals']) == 1
    assert len(state['evidence_links']) == 2
    assert state['boundaries']['automatic_truth_verification'] is False
    assert state['boundaries']['automatic_causality_inference'] is False

    assert client.get('/narrative-risk/decisions/dec-v370/claims', headers=_headers()).json()['count'] == 2
    assert client.get('/narrative-risk/decisions/dec-v370/signals', headers=_headers()).json()['count'] == 1
    assert client.get('/narrative-risk/decisions/dec-v370/evidence-links', headers=_headers()).json()['count'] == 2

    with Session(engine_for_url(url)) as session:
        claims = [r for r in session.scalars(select(Claim).where(Claim.decision_id == 'dec-v370')) if (r.metadata_json or {}).get('domain') == 'narrative-risk']
        assert len(claims) == 2
        assert all((r.metadata_json or {}).get('truth_verified') is False for r in claims)
        links = [r for r in session.scalars(select(EvidenceLink).where(EvidenceLink.decision_id == 'dec-v370')) if (r.metadata_json or {}).get('domain') == 'narrative-risk']
        assert len(links) == 2
        assert all((r.metadata_json or {}).get('causality_inferred') is False for r in links)
        signals = list(session.scalars(select(Artifact).where(Artifact.decision_id == 'dec-v370', Artifact.artifact_type == 'narrative-risk-signal')))
        assert len(signals) == 1
        assert signals[0].metadata_json['causality_inferred'] is False
        obj = session.scalar(select(DecisionObject).where(DecisionObject.decision_id == 'dec-v370', DecisionObject.object_type == 'narrative-risk-domain'))
        assert obj is not None and obj.schema_id == NARRATIVE_RISK_DOMAIN_SCHEMA
        module = session.get(DecisionModule, 'narrative-risk')
        assert module is not None and module.status == 'python-domain-authoritative'
        events = list(session.scalars(select(DecisionEvent).where(DecisionEvent.decision_id == 'dec-v370')))
        assert any(e.event_type == 'narrative_risk.domain.created' for e in events)


def test_v370_narrative_risk_signal_artifacts_do_not_delete_finance_receipts(monkeypatch, tmp_path):
    url = _decision(monkeypatch, tmp_path)
    finance = client.put('/finance/decisions/dec-v370', headers=_headers(), json={
        'workbench_receipts': [{'id': 'finance-r', 'uri': 'workbench://finance/run-1'}]
    })
    assert finance.status_code == 200, finance.text
    narrative = client.put('/narrative-risk/decisions/dec-v370', headers=_headers(), json={
        'signals': [{'id': 'sig-a', 'label': 'Initial risk signal'}]
    })
    assert narrative.status_code == 200, narrative.text
    narrative2 = client.put('/narrative-risk/decisions/dec-v370/signals', headers=_headers(), json={
        'signals': [{'id': 'sig-b', 'label': 'Updated risk signal'}]
    })
    assert narrative2.status_code == 200, narrative2.text
    finance_rows = client.get('/finance/decisions/dec-v370/workbench-receipts', headers=_headers()).json()['workbench_receipts']
    risk_rows = client.get('/narrative-risk/decisions/dec-v370/signals', headers=_headers()).json()['signals']
    assert len(finance_rows) == 1
    assert [x['label'] for x in risk_rows] == ['Updated risk signal']
    with Session(engine_for_url(url)) as session:
        artifacts = list(session.scalars(select(Artifact).where(Artifact.decision_id == 'dec-v370')))
        assert sorted(a.artifact_type for a in artifacts) == ['finance-workbench-receipt', 'narrative-risk-signal']


def test_v370_claim_replacement_removes_only_narrative_risk_links(monkeypatch, tmp_path):
    url = _decision(monkeypatch, tmp_path)
    initial = client.put('/narrative-risk/decisions/dec-v370', headers=_headers(), json={
        'claims': [{'id': 'a', 'text': 'Initial hypothesis'}],
        'evidence_links': [{'id': 'e', 'claim_id': 'a', 'evidence_ref': 'evidence:1'}],
    })
    assert initial.status_code == 200, initial.text
    repl = client.put('/narrative-risk/decisions/dec-v370/claims', headers=_headers(), json={
        'claims': [{'id': 'b', 'text': 'Replacement hypothesis'}]
    })
    assert repl.status_code == 200 and repl.json()['count'] == 1
    current = client.get('/narrative-risk/decisions/dec-v370', headers=_headers()).json()['narrative_risk']
    assert [x['text'] for x in current['claims']] == ['Replacement hypothesis']
    assert current['evidence_links'] == []
    with Session(engine_for_url(url)) as session:
        assert len(list(session.scalars(select(EvidenceLink).where(EvidenceLink.decision_id == 'dec-v370')))) == 0


def test_v370_legacy_narrative_risk_import_is_source_preserving(monkeypatch, tmp_path):
    _db(monkeypatch, tmp_path)
    artifact = {
        'decision_question': 'Which emerging narrative risks require review?',
        'context': {'market': 'regional'},
        'actors': [{'id': 'a1', 'name': 'Supplier'}],
        'risk_claims': [{'id': 'c1', 'text': 'Disruption risk may rise.', 'kind': 'risk-hypothesis'}],
        'indicators': [{'id': 's1', 'label': 'Outage chatter'}],
        'evidence_relationships': [{'id': 'l1', 'claim_id': 'c1', 'evidence_ref': 'library:e1', 'relation': 'context'}],
        'competing_narratives': [{'id': 'n1', 'label': 'Temporary disruption'}],
    }
    response = client.post('/narrative-risk/import/legacy', headers=_headers(), json={
        'artifact': artifact,
        'decision_id': 'legacy-risk-v370',
        'project_id': 'legacy-proj-v370',
        'project_title': 'Legacy Narrative Risk Migration',
        'provenance_ref': 'wp:narrative-risk',
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['created'] is True
    assert body['source_preserved'] is True
    assert body['narrative_risk']['provenance']['legacy_artifact']['context']['market'] == 'regional'
    assert body['narrative_risk']['claims'][0]['metadata']['truth_verified'] is False
    again = client.post('/narrative-risk/import/legacy', headers=_headers(), json={
        'artifact': {**artifact, 'context': {'market': 'global'}},
        'decision_id': 'legacy-risk-v370',
        'project_id': 'legacy-proj-v370',
    })
    assert again.status_code == 200
    assert again.json()['created'] is False
    assert again.json()['narrative_risk']['risk_context']['market'] == 'global'


def test_v370_route_inventory_preserves_v360_and_adds_narrative_risk_routes():
    current = json.loads((ROOT / 'data/backend_route_inventory_v3.7.0.json').read_text())
    previous = json.loads((ROOT / 'data/backend_route_inventory_v3.6.0.json').read_text())
    current_routes = {(r['path'], r['method']) for routes in current['routers'].values() for r in routes}
    previous_routes = {(r['path'], r['method']) for routes in previous['routers'].values() for r in routes}
    assert previous_routes <= current_routes
    assert current['route_count'] == 231
    assert len(current['routers']['narrative_risk']) == 11
    assert ('POST', '/narrative-risk/import/legacy') in {(r['method'], r['path']) for r in current['routers']['narrative_risk']}


def test_v370_schema_revision_is_unchanged():
    assert EXPECTED_SCHEMA_REVISION == '0002_v3130_collaboration'
