from __future__ import annotations

import json
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.domains.canvas import CANVAS_DOMAIN_SCHEMA
from app.persistence.database import EXPECTED_SCHEMA_REVISION, engine_for_url
from app.persistence.models import Alternative, Assumption, Criterion, DecisionEvent, DecisionModule, DecisionObject
from app.persistence.seed import seed_module_registry

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


def _db(monkeypatch, tmp_path):
    db = tmp_path / 'v350.sqlite3'
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


def _decision(monkeypatch, tmp_path, decision_id='dec-v350'):
    url = _db(monkeypatch, tmp_path)
    project = client.post('/repository/projects', headers=_headers(), json={
        'project_id': 'proj-v350', 'title': 'Canvas Migration Test'
    })
    assert project.status_code == 200, project.text
    decision = client.post('/repository/decisions', headers=_headers(), json={
        'decision_id': decision_id,
        'project_id': 'proj-v350',
        'decision_question': 'Which implementation pathway should be selected?'
    })
    assert decision.status_code == 200, decision.text
    return url


def test_v350_canvas_contract_and_release_boundary():
    health = client.get('/health').json()
    assert health['version'] == '3.14.0'
    assert health['canvas_domain_schema'] == CANVAS_DOMAIN_SCHEMA
    release = client.get('/release').json()['release']
    assert release['release_name'] == 'Global Authentication & Authorization Integration'
    assert release['build_fingerprint'] == 'scds-v3.14.0-global-authentication-authorization-integration'
    assert release['backend_architecture']['database_migration'] is False
    assert release['backend_architecture']['finance_python_domain_migration'] is False
    assert release['backend_architecture']['narrative_risk_python_domain_migration'] is False
    assert release['backend_architecture']['global_impact_python_domain_migration'] is False
    assert release['decision_kernel']['canvas_python_domain_authoritative'] is True
    assert release['canvas']['status'] == 'python-domain-authoritative'
    assert release['canvas']['final_decision_authority'] == 'human-governed'
    contract = client.get('/canvas/contract').json()['canvas_contract']
    assert contract['schema'] == CANVAS_DOMAIN_SCHEMA
    assert contract['storage_authority'] == 'python-postgresql'
    assert contract['boundaries']['automatic_winner_selection'] is False
    assert contract['boundaries']['automatic_recommendation'] is False


def test_v350_canvas_requires_scoped_auth(monkeypatch):
    monkeypatch.setenv('SCDS_REPOSITORY_API_KEY', 'test-repository-key')
    read = client.get('/canvas/decisions/example')
    assert read.status_code == 403
    assert read.json()['required_scope'] == 'canvas:read'
    write = client.put('/canvas/decisions/example', json={})
    assert write.status_code == 403
    assert write.json()['required_scope'] == 'canvas:write'


def test_v350_canvas_full_state_normalizes_shared_tables(monkeypatch, tmp_path):
    url = _decision(monkeypatch, tmp_path)
    payload = {
        'problem_statement': 'Choose a defensible pathway.',
        'decision_question': 'Which pathway best balances impact and cost?',
        'objective': 'Select a pathway for governed review.',
        'constraints': ['Budget ceiling', 'Implementation window'],
        'stakeholders': [{'role': 'decision-owner', 'name': 'Program lead'}],
        'success_measures': ['Evidence gaps visible', 'Criteria traceable'],
        'alternatives': [
            {'id': 'a', 'name': 'Pathway A', 'status': 'candidate'},
            {'id': 'b', 'name': 'Pathway B', 'status': 'candidate'},
        ],
        'criteria': [
            {'id': 'cost', 'name': 'Cost', 'weight': 0.4, 'direction': 'lower'},
            {'id': 'impact', 'name': 'Impact', 'weight': 0.6, 'direction': 'higher'},
        ],
        'assumptions': [
            {'id': 'schedule', 'statement': 'Permitting remains on schedule.', 'confidence': 'medium'}
        ],
        'evidence_refs': ['evidence:1'],
        'scenario_refs': ['scenario:baseline'],
        'provenance': {'source': 'test'},
        'provenance_ref': 'prov:canvas-test',
    }
    response = client.put('/canvas/decisions/dec-v350', headers=_headers(), json=payload)
    assert response.status_code == 200, response.text
    canvas = response.json()['canvas']
    assert canvas['schema'] == CANVAS_DOMAIN_SCHEMA
    assert canvas['decision_question'] == payload['decision_question']
    assert len(canvas['alternatives']) == 2
    assert len(canvas['criteria']) == 2
    assert len(canvas['assumptions']) == 1
    assert canvas['boundaries']['automatic_winner_selection'] is False

    # Dedicated list endpoints operate over normalized relational tables.
    assert client.get('/canvas/decisions/dec-v350/alternatives', headers=_headers()).json()['count'] == 2
    assert client.get('/canvas/decisions/dec-v350/criteria', headers=_headers()).json()['count'] == 2
    assert client.get('/canvas/decisions/dec-v350/assumptions', headers=_headers()).json()['count'] == 1

    with Session(engine_for_url(url)) as session:
        assert len(list(session.scalars(select(Alternative).where(Alternative.decision_id == 'dec-v350')))) == 2
        assert len(list(session.scalars(select(Criterion).where(Criterion.decision_id == 'dec-v350')))) == 2
        assert len(list(session.scalars(select(Assumption).where(Assumption.decision_id == 'dec-v350')))) == 1
        obj = session.scalar(select(DecisionObject).where(DecisionObject.decision_id == 'dec-v350', DecisionObject.object_type == 'canvas-domain'))
        assert obj is not None and obj.schema_id == CANVAS_DOMAIN_SCHEMA
        module = session.get(DecisionModule, 'canvas')
        assert module is not None and module.status == 'python-domain-authoritative'
        events = list(session.scalars(select(DecisionEvent).where(DecisionEvent.decision_id == 'dec-v350')))
        assert any(e.event_type == 'canvas.domain.created' for e in events)


def test_v350_canvas_subresource_replacement_keeps_domain_state_current(monkeypatch, tmp_path):
    _decision(monkeypatch, tmp_path)
    initial = client.put('/canvas/decisions/dec-v350', headers=_headers(), json={
        'alternatives': [{'id': 'a', 'name': 'A'}],
        'criteria': [{'id': 'c', 'name': 'Cost'}],
        'assumptions': [{'id': 'x', 'statement': 'Initial assumption'}],
    })
    assert initial.status_code == 200
    repl = client.put('/canvas/decisions/dec-v350/alternatives', headers=_headers(), json={
        'alternatives': [{'id': 'b', 'name': 'B'}, {'id': 'c', 'name': 'C'}]
    })
    assert repl.status_code == 200 and repl.json()['count'] == 2
    current = client.get('/canvas/decisions/dec-v350', headers=_headers()).json()['canvas']
    assert [x['name'] for x in current['alternatives']] == ['B', 'C']


def test_v350_legacy_catalyst_canvas_import_is_source_preserving(monkeypatch, tmp_path):
    _db(monkeypatch, tmp_path)
    artifact = {
        'challenge': 'How should the project be framed?',
        'audience': 'Decision reviewer',
        'goal': 'Create a traceable decision record',
        'constraint': 'Use only reviewed sources',
        'point_of_view': 'A reviewer needs a clear decision frame.',
        'how_might_we': ['How might we make the decision auditable?'],
        'prototype': {'title': 'Decision Packet'},
        'test_plan': {'signal': 'Reviewer can identify gaps'},
    }
    response = client.post('/canvas/import/legacy', headers=_headers(), json={
        'artifact': artifact,
        'decision_id': 'legacy-canvas-v350',
        'project_id': 'legacy-proj-v350',
        'project_title': 'Legacy Canvas Migration',
        'provenance_ref': 'wp:catalyst-canvas',
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['created'] is True
    assert body['source_preserved'] is True
    assert body['canvas']['problem_statement'] == artifact['challenge']
    assert body['canvas']['provenance']['legacy_artifact']['goal'] == artifact['goal']

    # Re-import is safe: existing decision becomes the target, not a duplicate identity.
    again = client.post('/canvas/import/legacy', headers=_headers(), json={
        'artifact': {**artifact, 'goal': 'Updated traceable decision record'},
        'decision_id': 'legacy-canvas-v350',
        'project_id': 'legacy-proj-v350',
    })
    assert again.status_code == 200
    assert again.json()['created'] is False
    assert again.json()['canvas']['objective'] == 'Updated traceable decision record'


def test_v350_route_inventory_preserves_v340_and_adds_canvas_routes():
    current = json.loads((ROOT / 'data/backend_route_inventory_v3.5.0.json').read_text())
    previous = json.loads((ROOT / 'data/backend_route_inventory_v3.4.0.json').read_text())
    current_routes = {(r['path'], r['method']) for routes in current['routers'].values() for r in routes}
    previous_routes = {(r['path'], r['method']) for routes in previous['routers'].values() for r in routes}
    assert previous_routes <= current_routes
    assert current['route_count'] == 209
    assert len(current['routers']['canvas']) == 11
    assert ('POST', '/canvas/import/legacy') in {(r['method'], r['path']) for r in current['routers']['canvas']}


def test_v350_schema_revision_is_unchanged():
    assert EXPECTED_SCHEMA_REVISION == '0002_v3130_collaboration'
