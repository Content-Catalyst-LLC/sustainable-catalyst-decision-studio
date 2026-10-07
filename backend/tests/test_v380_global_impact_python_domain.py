from __future__ import annotations

import json
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.domains.global_impact import GLOBAL_IMPACT_DOMAIN_SCHEMA
from app.persistence.database import EXPECTED_SCHEMA_REVISION, engine_for_url
from app.persistence.models import Artifact, Claim, DecisionEvent, DecisionModule, DecisionObject, EvidenceLink
from app.persistence.seed import seed_module_registry

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


def _db(monkeypatch, tmp_path):
    db = tmp_path / 'v380.sqlite3'
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


def _decision(monkeypatch, tmp_path, decision_id='dec-v380'):
    url = _db(monkeypatch, tmp_path)
    project = client.post('/repository/projects', headers=_headers(), json={
        'project_id': 'proj-v380', 'title': 'Global Impact Migration Test'
    })
    assert project.status_code == 200, project.text
    decision = client.post('/repository/decisions', headers=_headers(), json={
        'decision_id': decision_id,
        'project_id': 'proj-v380',
        'decision_question': 'Which option produces the most accountable impact profile?'
    })
    assert decision.status_code == 200, decision.text
    return url


def test_v380_global_impact_contract_and_release_boundary():
    health = client.get('/health').json()
    assert health['version'] == '3.8.0'
    assert health['global_impact_domain_schema'] == GLOBAL_IMPACT_DOMAIN_SCHEMA
    release = client.get('/release').json()['release']
    assert release['release_name'] == 'Global Impact Catalyst Python Domain Migration'
    assert release['build_fingerprint'] == 'scds-v3.8.0-global-impact-catalyst-python-domain-migration'
    assert release['backend_architecture']['database_migration'] is False
    assert release['backend_architecture']['global_impact_python_domain_migration'] is True
    assert release['decision_kernel']['global_impact_python_domain_authoritative'] is True
    assert release['decision_kernel']['global_impact_compute_authority'] == 'workbench'
    assert release['global_impact']['automatic_impact_verification'] is False
    assert release['global_impact']['automatic_sustainability_rating'] is False
    assert release['global_impact']['final_decision_authority'] == 'human-governed'
    contract = client.get('/global-impact/contract').json()['global_impact_contract']
    assert contract['schema'] == GLOBAL_IMPACT_DOMAIN_SCHEMA
    assert contract['storage_authority'] == 'python-postgresql'
    assert contract['compute_authority'] == 'workbench'
    assert contract['boundaries']['sdg_alignment_is_not_proof_of_impact'] is True
    assert contract['boundaries']['modeled_impact_is_not_observed_outcome'] is True
    assert contract['boundaries']['indicator_change_is_not_causal_attribution'] is True


def test_v380_global_impact_requires_scoped_auth(monkeypatch):
    monkeypatch.setenv('SCDS_REPOSITORY_API_KEY', 'test-repository-key')
    read = client.get('/global-impact/decisions/example')
    assert read.status_code == 403
    assert read.json()['required_scope'] == 'global-impact:read'
    write = client.put('/global-impact/decisions/example', json={})
    assert write.status_code == 403
    assert write.json()['required_scope'] == 'global-impact:write'


def test_v380_global_impact_normalizes_claims_indicators_and_evidence(monkeypatch, tmp_path):
    url = _decision(monkeypatch, tmp_path)
    payload = {
        'impact_context': {'scope': 'regional-transition'},
        'impact_objectives': [{'id': 'obj-1', 'label': 'Reduce lifecycle emissions'}],
        'impact_boundaries': {'time_horizon': '2035'},
        'stakeholders': [{'id': 's-1', 'name': 'Affected communities'}],
        'impact_pathways': [{'id': 'p-1', 'status': 'hypothesis'}],
        'environmental_impacts': [{'id': 'env-1', 'dimension': 'climate'}],
        'social_impacts': [{'id': 'soc-1', 'dimension': 'access'}],
        'economic_impacts': [{'id': 'econ-1', 'dimension': 'affordability'}],
        'sdg_alignments': [{'sdg': 'SDG 7', 'alignment': 'contextual'}],
        'carbon_context': {'boundary': 'lifecycle'},
        'resource_impacts': [{'id': 'r-1', 'resource': 'water'}],
        'distributional_impacts': [{'id': 'd-1', 'group': 'low-income households'}],
        'impact_claims': [
            {'id': 'claim-1', 'text': 'The intervention may reduce lifecycle emissions.', 'epistemic_status': 'unresolved', 'impact_dimension': 'environmental'},
            {'id': 'claim-2', 'text': 'Access may improve for underserved households.', 'epistemic_status': 'unresolved', 'impact_dimension': 'social'},
        ],
        'indicators': [
            {'id': 'ind-1', 'label': 'Lifecycle GHG intensity', 'unit': 'kgCO2e/unit', 'baseline': 100, 'target': 60, 'observed': False, 'source_ref': 'workspace:dataset:1'}
        ],
        'evidence_links': [
            {'id': 'link-1', 'claim_id': 'claim-1', 'evidence_ref': 'library:evidence:1', 'relation': 'supports'},
            {'id': 'link-2', 'claim_id': 'claim-2', 'evidence_ref': 'library:evidence:2', 'relation': 'context'},
        ],
        'provenance': {'source': 'test'},
        'provenance_ref': 'prov:global-impact-test',
    }
    response = client.put('/global-impact/decisions/dec-v380', headers=_headers(), json=payload)
    assert response.status_code == 200, response.text
    state = response.json()['global_impact']
    assert state['schema'] == GLOBAL_IMPACT_DOMAIN_SCHEMA
    assert len(state['impact_claims']) == 2
    assert len(state['indicators']) == 1
    assert len(state['evidence_links']) == 2
    assert state['boundaries']['automatic_impact_verification'] is False
    assert state['boundaries']['automatic_sustainability_rating'] is False

    assert client.get('/global-impact/decisions/dec-v380/impact-claims', headers=_headers()).json()['count'] == 2
    assert client.get('/global-impact/decisions/dec-v380/indicators', headers=_headers()).json()['count'] == 1
    assert client.get('/global-impact/decisions/dec-v380/evidence-links', headers=_headers()).json()['count'] == 2

    with Session(engine_for_url(url)) as session:
        claims = [r for r in session.scalars(select(Claim).where(Claim.decision_id == 'dec-v380')) if (r.metadata_json or {}).get('domain') == 'global-impact']
        assert len(claims) == 2
        assert all((r.metadata_json or {}).get('impact_verified') is False for r in claims)
        links = [r for r in session.scalars(select(EvidenceLink).where(EvidenceLink.decision_id == 'dec-v380')) if (r.metadata_json or {}).get('domain') == 'global-impact']
        assert len(links) == 2
        assert all((r.metadata_json or {}).get('causal_attribution_verified') is False for r in links)
        indicators = list(session.scalars(select(Artifact).where(Artifact.decision_id == 'dec-v380', Artifact.artifact_type == 'global-impact-indicator')))
        assert len(indicators) == 1
        assert indicators[0].metadata_json['causal_attribution_verified'] is False
        obj = session.scalar(select(DecisionObject).where(DecisionObject.decision_id == 'dec-v380', DecisionObject.object_type == 'global-impact-domain'))
        assert obj is not None and obj.schema_id == GLOBAL_IMPACT_DOMAIN_SCHEMA
        module = session.get(DecisionModule, 'global-impact')
        assert module is not None and module.status == 'python-domain-authoritative'
        events = list(session.scalars(select(DecisionEvent).where(DecisionEvent.decision_id == 'dec-v380')))
        assert any(e.event_type == 'global_impact.domain.created' for e in events)


def test_v380_global_impact_artifact_replacement_preserves_other_domains(monkeypatch, tmp_path):
    url = _decision(monkeypatch, tmp_path)
    finance = client.put('/finance/decisions/dec-v380', headers=_headers(), json={
        'workbench_receipts': [{'id': 'finance-r', 'uri': 'workbench://finance/run-1'}]
    })
    assert finance.status_code == 200, finance.text
    narrative = client.put('/narrative-risk/decisions/dec-v380', headers=_headers(), json={
        'signals': [{'id': 'risk-s', 'label': 'Policy uncertainty signal'}]
    })
    assert narrative.status_code == 200, narrative.text
    impact = client.put('/global-impact/decisions/dec-v380', headers=_headers(), json={
        'indicators': [{'id': 'impact-a', 'label': 'Water intensity'}]
    })
    assert impact.status_code == 200, impact.text
    impact2 = client.put('/global-impact/decisions/dec-v380/indicators', headers=_headers(), json={
        'indicators': [{'id': 'impact-b', 'label': 'Lifecycle GHG intensity'}]
    })
    assert impact2.status_code == 200, impact2.text
    assert len(client.get('/finance/decisions/dec-v380/workbench-receipts', headers=_headers()).json()['workbench_receipts']) == 1
    assert len(client.get('/narrative-risk/decisions/dec-v380/signals', headers=_headers()).json()['signals']) == 1
    assert [x['label'] for x in client.get('/global-impact/decisions/dec-v380/indicators', headers=_headers()).json()['indicators']] == ['Lifecycle GHG intensity']
    with Session(engine_for_url(url)) as session:
        artifacts = list(session.scalars(select(Artifact).where(Artifact.decision_id == 'dec-v380')))
        assert sorted(a.artifact_type for a in artifacts) == ['finance-workbench-receipt', 'global-impact-indicator', 'narrative-risk-signal']


def test_v380_legacy_global_impact_import_is_source_preserving(monkeypatch, tmp_path):
    _db(monkeypatch, tmp_path)
    artifact = {
        'decision_question': 'Which option best advances accountable regional impact?',
        'context': {'geography': 'regional'},
        'impact_objectives': [{'id': 'o1', 'label': 'Lower emissions'}],
        'sdg_alignment': [{'sdg': 'SDG 7'}],
        'carbon_impact': {'boundary': 'lifecycle'},
        'impact_claims': [{'id': 'c1', 'text': 'Lifecycle emissions may decline.'}],
        'indicators': [{'id': 'i1', 'label': 'Lifecycle emissions', 'unit': 'tCO2e'}],
        'evidence_relationships': [{'id': 'e1', 'claim_id': 'c1', 'evidence_ref': 'library:e1'}],
    }
    response = client.post('/global-impact/import/legacy', headers=_headers(), json={
        'artifact': artifact,
        'decision_id': 'legacy-impact-v380',
        'project_id': 'legacy-proj-v380',
        'project_title': 'Legacy Global Impact Migration',
        'provenance_ref': 'wp:global-impact',
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['created'] is True
    assert body['source_preserved'] is True
    assert body['global_impact']['provenance']['legacy_artifact']['context']['geography'] == 'regional'
    assert body['global_impact']['impact_claims'][0]['metadata']['impact_verified'] is False
    again = client.post('/global-impact/import/legacy', headers=_headers(), json={
        'artifact': {**artifact, 'context': {'geography': 'global'}},
        'decision_id': 'legacy-impact-v380',
        'project_id': 'legacy-proj-v380',
    })
    assert again.status_code == 200
    assert again.json()['created'] is False
    assert again.json()['global_impact']['impact_context']['geography'] == 'global'


def test_v380_route_inventory_preserves_v370_and_adds_global_impact_routes():
    current = json.loads((ROOT / 'data/backend_route_inventory_v3.8.0.json').read_text())
    previous = json.loads((ROOT / 'data/backend_route_inventory_v3.7.0.json').read_text())
    current_routes = {(r['path'], r['method']) for routes in current['routers'].values() for r in routes}
    previous_routes = {(r['path'], r['method']) for routes in previous['routers'].values() for r in routes}
    assert previous_routes <= current_routes
    assert current['route_count'] == 242
    assert len(current['routers']['global_impact']) == 11
    assert ('POST', '/global-impact/import/legacy') in {(r['method'], r['path']) for r in current['routers']['global_impact']}


def test_v380_schema_revision_is_unchanged():
    assert EXPECTED_SCHEMA_REVISION == '0001_v330_pg_foundation'
