from __future__ import annotations

import json
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.cross_module_composition import (
    CROSS_MODULE_COMPOSITION_OBJECT_TYPE,
    CROSS_MODULE_COMPOSITION_SCHEMA,
    CompositionUpsertRequest,
    CrossModuleCompositionRepository,
)
from app.domains.canvas import CanvasDomainRepository, CanvasStateUpsert
from app.domains.finance import FinanceDomainRepository, FinanceStateUpsert
from app.domains.global_impact import GlobalImpactDomainRepository, GlobalImpactStateUpsert
from app.domains.narrative_risk import NarrativeRiskDomainRepository, NarrativeRiskStateUpsert
from app.main import app
from app.persistence.database import EXPECTED_SCHEMA_REVISION, session_scope
from app.persistence.models import DecisionObject
from app.persistence.repository import PersistenceRepository
from app.persistence.seed import seed_module_registry

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


def _db(monkeypatch, tmp_path):
    db = tmp_path / 'v3100.sqlite3'
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
    return {'x-scds-api-key': 'test-repository-key'}


def _seed_four_domains():
    with session_scope() as session:
        repo = PersistenceRepository(session)
        repo.create_project(project_id='proj-compose', title='Composition project')
        repo.create_decision(decision_id='dec-compose', project_id='proj-compose', decision_question='Which pathway should we pursue?')
        CanvasDomainRepository(session).upsert_canvas('dec-compose', CanvasStateUpsert(
            problem_statement='Choose a pathway',
            alternatives=[{'id':'alt-a','name':'Pathway A'},{'id':'alt-b','name':'Pathway B'}],
            criteria=[{'id':'crit-a','name':'Resilience','weight':'0.5'}],
            assumptions=[{'id':'asm-c','statement':'Demand remains stable'}],
        ))
        FinanceDomainRepository(session).upsert_finance('dec-compose', FinanceStateUpsert(
            assumptions=[{'id':'asm-f','statement':'Discount rate remains within range'}],
            scenarios=[{'id':'fin-s1','name':'Base case'}],
            workbench_receipts=[{'id':'wb-1','label':'NPV run','status':'complete'}],
        ))
        NarrativeRiskDomainRepository(session).upsert_narrative_risk('dec-compose', NarrativeRiskStateUpsert(
            claims=[{'id':'risk-c1','text':'Supplier concentration may increase disruption exposure'}],
            signals=[{'id':'risk-s1','label':'Supplier lead-time signal'}],
            evidence_links=[{'id':'risk-e1','claim_ref':'risk-c1','evidence_ref':'evidence:supplier-1','relation':'supports'}],
        ))
        GlobalImpactDomainRepository(session).upsert_global_impact('dec-compose', GlobalImpactStateUpsert(
            impact_claims=[{'id':'impact-c1','text':'Pathway A may reduce lifecycle emissions'}],
            indicators=[{'id':'impact-i1','label':'Lifecycle tCO2e','unit':'tCO2e'}],
            evidence_links=[{'id':'impact-e1','claim_ref':'impact-c1','evidence_ref':'evidence:lca-1','relation':'context'}],
        ))


def test_v3100_release_identity_and_composition_schema():
    health = client.get('/health').json()
    assert health['version'] == '3.15.0'
    assert health['cross_module_decision_composition_schema'] == CROSS_MODULE_COMPOSITION_SCHEMA
    release = client.get('/release').json()['release']
    assert release['release_name'] == 'Decision Event Store & Immutable Audit Ledger'
    assert release['build_fingerprint'] == 'scds-v3.15.0-decision-event-store-immutable-audit-ledger'
    assert release['backend_architecture']['database_migration'] is True
    assert release['backend_architecture']['cross_module_decision_composition'] is True
    assert release['backend_architecture']['composition_infers_truth'] is False
    assert release['backend_architecture']['composition_auto_recommends'] is False


def test_v3100_contract_preserves_ownership_and_human_boundaries():
    contract = client.get('/decision-composition/contract').json()['composition_contract']
    assert contract['schema'] == CROSS_MODULE_COMPOSITION_SCHEMA
    assert contract['minimum_modules'] == 2
    assert contract['principles']['module_objects_retain_domain_ownership'] is True
    assert contract['principles']['composition_links_are_explicit_not_inferred'] is True
    assert contract['principles']['composition_does_not_infer_causality'] is True
    assert contract['principles']['composition_does_not_auto_recommend'] is True
    assert contract['principles']['composition_does_not_auto_approve'] is True
    assert contract['compute_authorities'] == {'finance':'workbench','global-impact':'workbench'}
    assert contract['final_decision_authority'] == 'human-governed'


def test_v3100_authoritative_cross_module_composition(monkeypatch, tmp_path):
    headers = _db(monkeypatch, tmp_path)
    _seed_four_domains()
    payload = {
        'module_ids':['canvas','finance','narrative-risk','global-impact'],
        'title':'Four-lens decision composition',
        'purpose':'Review the same decision across all authoritative modules.',
        'cross_module_links':[
            {
                'relation':'tradeoff',
                'source_module':'finance','source_ref':'wb-1',
                'target_module':'global-impact','target_ref':'impact-i1',
                'note':'Compare financial value and lifecycle impact without merging either authority.'
            },
            {
                'relation':'risk-context',
                'source_module':'narrative-risk','source_ref':'risk-c1',
                'target_module':'canvas','target_ref':'alt-a'
            }
        ]
    }
    response = client.put('/decision-composition/decisions/dec-compose', json=payload, headers=headers)
    assert response.status_code == 200, response.text
    composition = response.json()['composition']
    assert composition['schema'] == CROSS_MODULE_COMPOSITION_SCHEMA
    assert composition['selected_modules'] == ['canvas','finance','narrative-risk','global-impact']
    assert composition['diagnostics']['composition_ready'] is True
    assert composition['diagnostics']['cross_module_link_count'] == 2
    assert composition['diagnostics']['inferred_truth'] is False
    assert composition['diagnostics']['inferred_causality'] is False
    assert composition['diagnostics']['automatic_recommendation'] is False
    projection = composition['shared_kernel_projection']
    assumption_owners = {item['module_id'] for item in projection['assumptions']}
    claim_owners = {item['module_id'] for item in projection['claims']}
    artifact_owners = {item['module_id'] for item in projection['artifacts']}
    assert assumption_owners == {'canvas','finance'}
    assert claim_owners == {'narrative-risk','global-impact'}
    assert {'finance','narrative-risk','global-impact'} <= artifact_owners
    assert composition['module_snapshots']['finance']['authorities']['compute_authority'] == 'workbench'
    assert composition['module_snapshots']['global-impact']['authorities']['compute_authority'] == 'workbench'

    with session_scope() as session:
        row = session.scalar(select(DecisionObject).where(
            DecisionObject.decision_id == 'dec-compose',
            DecisionObject.object_type == CROSS_MODULE_COMPOSITION_OBJECT_TYPE,
        ))
        assert row is not None
        assert row.schema_id == CROSS_MODULE_COMPOSITION_SCHEMA


def test_v3100_diagnostics_detect_stale_module_and_refresh(monkeypatch, tmp_path):
    headers = _db(monkeypatch, tmp_path)
    _seed_four_domains()
    put = client.put('/decision-composition/decisions/dec-compose', json={
        'module_ids':['canvas','finance'],
        'cross_module_links':[{
            'relation':'assumption-context',
            'source_module':'finance','source_ref':'asm-f',
            'target_module':'canvas','target_ref':'asm-c'
        }]
    }, headers=headers)
    assert put.status_code == 200
    with session_scope() as session:
        CanvasDomainRepository(session).replace_assumptions('dec-compose', [
            {'id':'asm-c2','statement':'Demand grows modestly'}
        ])
    diag = client.get('/decision-composition/decisions/dec-compose/diagnostics', headers=headers)
    assert diag.status_code == 200
    assert diag.json()['diagnostics']['stale_modules'] == ['canvas']
    refreshed = client.post('/decision-composition/decisions/dec-compose/refresh', headers=headers)
    assert refreshed.status_code == 200
    assert refreshed.json()['composition']['revision'] == 2
    diag2 = client.get('/decision-composition/decisions/dec-compose/diagnostics', headers=headers).json()['diagnostics']
    assert diag2['stale_modules'] == []


def test_v3100_validation_rejects_implicit_or_invalid_composition():
    template = client.get('/decision-composition/template').json()['composition']
    template['selected_modules'] = ['canvas']
    bad = client.post('/decision-composition/validate', json={'composition': template, 'strict': True}).json()
    assert bad['ok'] is False
    assert 'at_least_two_modules_required' in bad['errors']

    template['selected_modules'] = ['canvas','finance']
    template['module_snapshots'] = {'canvas':{}, 'finance':{}}
    template['cross_module_links'] = [{
        'relation':'tradeoff','source_module':'canvas','source_ref':'a',
        'target_module':'canvas','target_ref':'b'
    }]
    bad2 = client.post('/decision-composition/validate', json={'composition': template, 'strict': True}).json()
    assert bad2['ok'] is False
    assert 'link_must_be_cross_module:0' in bad2['errors']


def test_v3100_composition_routes_and_v390_preservation():
    current = json.loads((ROOT / 'data/backend_route_inventory_v3.12.0.json').read_text())
    previous = json.loads((ROOT / 'data/backend_route_inventory_v3.9.0.json').read_text())
    current_routes = {(r['path'], r['method']) for routes in current['routers'].values() for r in routes}
    previous_routes = {(r['path'], r['method']) for routes in previous['routers'].values() for r in routes}
    assert previous_routes <= current_routes
    assert current['route_count'] == 272
    assert len(current['routers']) == 23
    assert len(current['routers']['composition']) == 7
    assert ('PUT','/decision-composition/decisions/{decision_id}') in {(r['method'],r['path']) for r in current['routers']['composition']}


def test_v3100_schema_revision_is_unchanged():
    assert EXPECTED_SCHEMA_REVISION == '0003_v3150_event_ledger'
