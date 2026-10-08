from __future__ import annotations

import json
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.domains.finance import FINANCE_DOMAIN_SCHEMA
from app.persistence.database import EXPECTED_SCHEMA_REVISION, engine_for_url
from app.persistence.models import (
    Artifact,
    Assumption,
    DecisionEvent,
    DecisionModule,
    DecisionObject,
    Scenario,
    ScenarioVariable,
    UncertaintyModel,
)
from app.persistence.seed import seed_module_registry

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


def _db(monkeypatch, tmp_path):
    db = tmp_path / 'v360.sqlite3'
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


def _decision(monkeypatch, tmp_path, decision_id='dec-v360'):
    url = _db(monkeypatch, tmp_path)
    project = client.post('/repository/projects', headers=_headers(), json={
        'project_id': 'proj-v360', 'title': 'Finance Migration Test'
    })
    assert project.status_code == 200, project.text
    decision = client.post('/repository/decisions', headers=_headers(), json={
        'decision_id': decision_id,
        'project_id': 'proj-v360',
        'decision_question': 'Which financing pathway should be reviewed?'
    })
    assert decision.status_code == 200, decision.text
    return url


def test_v360_finance_contract_and_release_boundary():
    health = client.get('/health').json()
    assert health['version'] == '3.15.0'
    assert health['finance_domain_schema'] == FINANCE_DOMAIN_SCHEMA
    release = client.get('/release').json()['release']
    assert release['release_name'] == 'Decision Event Store & Immutable Audit Ledger'
    assert release['build_fingerprint'] == 'scds-v3.15.0-decision-event-store-immutable-audit-ledger'
    assert release['backend_architecture']['database_migration'] is True
    assert release['backend_architecture']['finance_python_domain_migration'] is False
    assert release['backend_architecture']['narrative_risk_python_domain_migration'] is False
    assert release['backend_architecture']['global_impact_python_domain_migration'] is False
    assert release['backend_architecture']['canvas_python_domain_migration'] is False
    assert release['finance']['status'] == 'python-domain-authoritative'
    assert release['finance']['compute_authority'] == 'workbench'
    assert release['finance']['decision_studio_executes_financial_models'] is False
    assert release['finance']['final_decision_authority'] == 'human-governed'
    contract = client.get('/finance/contract').json()['finance_contract']
    assert contract['schema'] == FINANCE_DOMAIN_SCHEMA
    assert contract['storage_authority'] == 'python-postgresql'
    assert contract['compute_authority'] == 'workbench'
    assert contract['boundaries']['decision_studio_executes_financial_models'] is False
    assert contract['boundaries']['model_output_is_automatic_recommendation'] is False


def test_v360_finance_requires_scoped_auth(monkeypatch):
    monkeypatch.setenv('SCDS_REPOSITORY_API_KEY', 'test-repository-key')
    read = client.get('/finance/decisions/example')
    assert read.status_code == 403
    assert read.json()['required_scope'] == 'finance:read'
    write = client.put('/finance/decisions/example', json={})
    assert write.status_code == 403
    assert write.json()['required_scope'] == 'finance:write'


def test_v360_finance_full_state_normalizes_shared_tables(monkeypatch, tmp_path):
    url = _decision(monkeypatch, tmp_path)
    payload = {
        'currency': 'usd',
        'base_year': 2026,
        'horizon_years': 8,
        'capital_context': {'capex_ref': 'input:capex'},
        'cost_context': {'opex_ref': 'input:opex'},
        'revenue_context': {'revenue_ref': 'input:revenue'},
        'discounting_context': {'discount_rate_ref': 'input:wacc'},
        'model_refs': ['workbench:model:cashflow'],
        'valuation_refs': ['workbench:result:npv'],
        'cost_benefit_refs': ['workbench:result:bcr'],
        'assumptions': [
            {'id': 'price', 'statement': 'Energy price remains within the modeled band.', 'confidence': 'medium'}
        ],
        'scenarios': [
            {
                'id': 'base', 'name': 'Base case', 'status': 'active',
                'variables': [
                    {'id': 'price', 'name': 'Energy price', 'value': {'amount': 80, 'unit': 'USD/MWh'}, 'source_ref': 'dataset:price'}
                ]
            }
        ],
        'uncertainty_models': [
            {
                'id': 'cost-vol', 'model_type': 'financial-input-uncertainty',
                'specification': {'variable': 'capex', 'distribution': 'triangular'},
                'computation_ref': 'workbench:uncertainty:001',
            }
        ],
        'workbench_receipts': [
            {
                'id': 'run-1', 'uri': 'workbench://jobs/run-1',
                'checksum_sha256': 'a' * 64,
                'metadata': {'runtime': 'python', 'result_kind': 'valuation'}
            }
        ],
        'evidence_refs': ['evidence:finance:1'],
        'provenance': {'source': 'test'},
        'provenance_ref': 'prov:finance-test',
    }
    response = client.put('/finance/decisions/dec-v360', headers=_headers(), json=payload)
    assert response.status_code == 200, response.text
    finance = response.json()['finance']
    assert finance['schema'] == FINANCE_DOMAIN_SCHEMA
    assert finance['currency'] == 'USD'
    assert len(finance['assumptions']) == 1
    assert len(finance['scenarios']) == 1
    assert len(finance['uncertainty_models']) == 1
    assert len(finance['workbench_receipts']) == 1
    assert finance['authorities']['compute_authority'] == 'workbench'
    assert finance['boundaries']['decision_studio_executes_financial_models'] is False

    assert client.get('/finance/decisions/dec-v360/assumptions', headers=_headers()).json()['count'] == 1
    assert client.get('/finance/decisions/dec-v360/scenarios', headers=_headers()).json()['count'] == 1
    assert client.get('/finance/decisions/dec-v360/workbench-receipts', headers=_headers()).json()['count'] == 1

    with Session(engine_for_url(url)) as session:
        finance_assumptions = [r for r in session.scalars(select(Assumption).where(Assumption.decision_id == 'dec-v360')) if (r.metadata_json or {}).get('domain') == 'finance']
        assert len(finance_assumptions) == 1
        finance_scenarios = [r for r in session.scalars(select(Scenario).where(Scenario.decision_id == 'dec-v360')) if (r.metadata_json or {}).get('domain') == 'finance']
        assert len(finance_scenarios) == 1
        variables = list(session.scalars(select(ScenarioVariable).where(ScenarioVariable.scenario_id == finance_scenarios[0].id)))
        assert len(variables) == 1
        uncertainty = [r for r in session.scalars(select(UncertaintyModel).where(UncertaintyModel.decision_id == 'dec-v360')) if (r.specification or {}).get('domain') == 'finance']
        assert len(uncertainty) == 1
        receipts = list(session.scalars(select(Artifact).where(Artifact.decision_id == 'dec-v360', Artifact.artifact_type == 'finance-workbench-receipt')))
        assert len(receipts) == 1
        assert receipts[0].metadata_json['compute_authority'] == 'workbench'
        obj = session.scalar(select(DecisionObject).where(DecisionObject.decision_id == 'dec-v360', DecisionObject.object_type == 'finance-domain'))
        assert obj is not None and obj.schema_id == FINANCE_DOMAIN_SCHEMA
        module = session.get(DecisionModule, 'finance')
        assert module is not None and module.status == 'python-domain-authoritative'
        assert module.contract_json['providers']['compute_authority'] == 'workbench'
        events = list(session.scalars(select(DecisionEvent).where(DecisionEvent.decision_id == 'dec-v360')))
        assert any(e.event_type == 'finance.domain.created' for e in events)


def test_v360_finance_and_canvas_assumptions_are_isolated(monkeypatch, tmp_path):
    url = _decision(monkeypatch, tmp_path)
    canvas = client.put('/canvas/decisions/dec-v360', headers=_headers(), json={
        'assumptions': [{'id': 'canvas-a', 'statement': 'Canvas framing assumption'}]
    })
    assert canvas.status_code == 200, canvas.text
    finance = client.put('/finance/decisions/dec-v360', headers=_headers(), json={
        'assumptions': [{'id': 'finance-a', 'statement': 'Finance model assumption'}]
    })
    assert finance.status_code == 200, finance.text

    # Updating Canvas after Finance must not delete Finance-owned shared-table rows.
    canvas2 = client.put('/canvas/decisions/dec-v360/assumptions', headers=_headers(), json={
        'assumptions': [{'id': 'canvas-b', 'statement': 'Updated Canvas assumption'}]
    })
    assert canvas2.status_code == 200, canvas2.text
    finance_rows = client.get('/finance/decisions/dec-v360/assumptions', headers=_headers()).json()['assumptions']
    canvas_rows = client.get('/canvas/decisions/dec-v360/assumptions', headers=_headers()).json()['assumptions']
    assert [x['statement'] for x in finance_rows] == ['Finance model assumption']
    assert [x['statement'] for x in canvas_rows] == ['Updated Canvas assumption']

    with Session(engine_for_url(url)) as session:
        rows = list(session.scalars(select(Assumption).where(Assumption.decision_id == 'dec-v360')))
        domains = sorted((r.metadata_json or {}).get('domain') for r in rows)
        assert domains == ['canvas', 'finance']


def test_v360_finance_subresource_replacement_keeps_domain_state_current(monkeypatch, tmp_path):
    _decision(monkeypatch, tmp_path)
    initial = client.put('/finance/decisions/dec-v360', headers=_headers(), json={
        'assumptions': [{'id': 'a', 'statement': 'Initial finance assumption'}],
        'scenarios': [{'id': 's', 'name': 'Initial scenario'}],
        'workbench_receipts': [{'id': 'r', 'uri': 'workbench://run/r'}],
    })
    assert initial.status_code == 200, initial.text
    repl = client.put('/finance/decisions/dec-v360/scenarios', headers=_headers(), json={
        'scenarios': [{'id': 'up', 'name': 'Upside'}, {'id': 'down', 'name': 'Downside'}]
    })
    assert repl.status_code == 200 and repl.json()['count'] == 2
    current = client.get('/finance/decisions/dec-v360', headers=_headers()).json()['finance']
    assert [x['name'] for x in current['scenarios']] == ['Upside', 'Downside']
    assert len(current['assumptions']) == 1
    assert len(current['workbench_receipts']) == 1


def test_v360_legacy_catalyst_finance_import_is_source_preserving(monkeypatch, tmp_path):
    _db(monkeypatch, tmp_path)
    artifact = {
        'decision_question': 'Which financing structure should be reviewed?',
        'currency': 'EUR',
        'base_year': 2026,
        'model_years': 10,
        'capital': {'capex': 1000000},
        'costs': {'annual_opex': 50000},
        'revenues': {'annual_revenue': 180000},
        'discounting': {'rate': 0.07},
        'financial_assumptions': [{'id': 'growth', 'statement': 'Revenue grows at modeled rate.'}],
        'financial_scenarios': [{'id': 'base', 'name': 'Base case'}],
        'workbench_result_ref': 'workbench://legacy/valuation-1',
    }
    response = client.post('/finance/import/legacy', headers=_headers(), json={
        'artifact': artifact,
        'decision_id': 'legacy-finance-v360',
        'project_id': 'legacy-proj-v360',
        'project_title': 'Legacy Finance Migration',
        'provenance_ref': 'wp:catalyst-finance',
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['created'] is True
    assert body['source_preserved'] is True
    assert body['finance']['currency'] == 'EUR'
    assert body['finance']['provenance']['legacy_artifact']['capital']['capex'] == 1000000
    assert body['finance']['workbench_receipts'][0]['metadata']['compute_authority'] == 'workbench'

    again = client.post('/finance/import/legacy', headers=_headers(), json={
        'artifact': {**artifact, 'model_years': 12},
        'decision_id': 'legacy-finance-v360',
        'project_id': 'legacy-proj-v360',
    })
    assert again.status_code == 200
    assert again.json()['created'] is False
    assert again.json()['finance']['horizon_years'] == 12


def test_v360_route_inventory_preserves_v350_and_adds_finance_routes():
    current = json.loads((ROOT / 'data/backend_route_inventory_v3.6.0.json').read_text())
    previous = json.loads((ROOT / 'data/backend_route_inventory_v3.5.0.json').read_text())
    current_routes = {(r['path'], r['method']) for routes in current['routers'].values() for r in routes}
    previous_routes = {(r['path'], r['method']) for routes in previous['routers'].values() for r in routes}
    assert previous_routes <= current_routes
    assert current['route_count'] == 220
    assert len(current['routers']['finance']) == 11
    assert ('POST', '/finance/import/legacy') in {(r['method'], r['path']) for r in current['routers']['finance']}


def test_v360_schema_revision_is_unchanged():
    assert EXPECTED_SCHEMA_REVISION == '0003_v3150_event_ledger'
