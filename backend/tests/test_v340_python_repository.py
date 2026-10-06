from __future__ import annotations

import json
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.main import app
from app.persistence.contracts import REPOSITORY_SCHEMA
from app.persistence.database import EXPECTED_SCHEMA_REVISION, engine_for_url
from app.persistence.models import DecisionEvent, DecisionModule
from app.persistence.seed import seed_module_registry
from sqlalchemy import select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


def _db(monkeypatch, tmp_path):
    db = tmp_path / 'v340.sqlite3'
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


def test_v340_authority_contract_moves_storage_not_human_decision_authority():
    body = client.get('/persistence/contract').json()['persistence_contract']
    assert body['authority'] == 'python-postgresql'
    assert body['repository_schema'] == REPOSITORY_SCHEMA
    principles = body['principles']
    assert principles['postgresql_is_live_authority'] is True
    assert principles['python_repository_is_live_authority'] is True
    assert principles['wordpress_decision_object_authority_changed'] is True
    assert principles['wordpress_legacy_packet_storage_preserved'] is True
    assert principles['v3_4_authority_cutover_complete'] is True
    assert principles['final_decision_authority'] == 'human-governed'


def test_v340_repository_crud_object_binding_snapshot_and_import(monkeypatch, tmp_path):
    url = _db(monkeypatch, tmp_path)
    headers = {'x-scds-api-key': 'test-repository-key'}

    authority = client.get('/repository/authority')
    assert authority.status_code == 200
    auth_body = authority.json()
    assert auth_body['ok'] is True
    assert auth_body['repository']['schema'] == REPOSITORY_SCHEMA
    assert auth_body['repository']['storage_authority'] == 'python-postgresql'
    assert auth_body['repository']['final_decision_authority'] == 'human-governed'
    assert auth_body['persistence']['schema_revision'] == EXPECTED_SCHEMA_REVISION
    assert auth_body['persistence']['authority_ready'] is True

    project = client.post('/repository/projects', headers=headers, json={
        'project_id': 'proj-v340',
        'title': 'Repository Cutover Test',
        'owner_ref': 'user:test',
    })
    assert project.status_code == 200, project.text
    assert project.json()['project']['id'] == 'proj-v340'

    decision = client.post('/repository/decisions', headers=headers, json={
        'decision_id': 'dec-v340',
        'project_id': 'proj-v340',
        'decision_question': 'Which pathway should be selected?',
        'metadata': {'source': 'test'},
    })
    assert decision.status_code == 200, decision.text
    assert decision.json()['decision']['final_decision_authority'] == 'human-governed'

    obj_payload = {
        'schema': 'scds-decision-object/1.0',
        'decision_id': 'dec-v340',
        'status': 'draft',
        'question': 'Which pathway should be selected?',
        'alternatives': [{'id': 'a'}],
        'criteria': [{'id': 'cost'}],
    }
    put_obj = client.put('/repository/decisions/dec-v340/object', headers=headers, json={
        'payload': obj_payload,
        'provenance_ref': 'prov:test',
    })
    assert put_obj.status_code == 200, put_obj.text
    assert put_obj.json()['decision_object']['payload']['decision_id'] == 'dec-v340'

    get_obj = client.get('/repository/decisions/dec-v340/object', headers=headers)
    assert get_obj.status_code == 200
    assert get_obj.json()['decision_object']['schema_id'] == 'scds-decision-object/1.0'

    binding = client.put('/repository/decisions/dec-v340/modules/finance', headers=headers, json={
        'enabled': True,
        'configuration': {'compute_authority': 'workbench'},
    })
    assert binding.status_code == 200, binding.text
    assert binding.json()['binding']['module_id'] == 'finance'

    snap = client.post('/repository/decisions/dec-v340/snapshots', headers=headers, json={
        'snapshot_type': 'decision',
        'payload': obj_payload,
        'provenance_ref': 'prov:snapshot',
    })
    assert snap.status_code == 200, snap.text
    current = client.get('/repository/decisions/dec-v340/snapshot', headers=headers)
    assert current.status_code == 200
    assert current.json()['snapshot']['id'] == snap.json()['snapshot']['id']

    patch = client.patch('/repository/decisions/dec-v340', headers=headers, json={'lifecycle_state': 'analysis'})
    assert patch.status_code == 200
    assert patch.json()['decision']['lifecycle_state'] == 'analysis'

    imported = client.post('/repository/import/decision-object', headers=headers, json={
        'decision_object': {
            'schema': 'scds-decision-object/1.0',
            'decision_id': 'legacy-v340',
            'status': 'draft',
            'question': 'Imported legacy decision?',
            'alternatives': [],
            'criteria': [],
        },
        'project_id': 'legacy-project',
        'project_title': 'Legacy import project',
        'provenance_ref': 'wp:legacy-object',
    })
    assert imported.status_code == 200, imported.text
    assert imported.json()['created'] is True
    assert imported.json()['source_preserved'] is True
    assert imported.json()['decision']['id'] == 'legacy-v340'

    imported_again = client.post('/repository/import/decision-object', headers=headers, json={
        'decision_object': {
            'schema': 'scds-decision-object/1.0',
            'decision_id': 'legacy-v340',
            'status': 'analysis',
            'question': 'Imported legacy decision updated?',
        },
        'project_id': 'legacy-project',
    })
    assert imported_again.status_code == 200
    assert imported_again.json()['created'] is False
    assert imported_again.json()['idempotent'] is True

    with Session(engine_for_url(url)) as session:
        modules = list(session.scalars(select(DecisionModule)))
        assert {m.module_id for m in modules} == {'canvas', 'finance', 'narrative-risk', 'global-impact'}
        events = list(session.scalars(select(DecisionEvent).where(DecisionEvent.decision_id == 'dec-v340')))
        assert len(events) >= 5


def test_v340_repository_write_guard(monkeypatch):
    monkeypatch.delenv('SCDS_DATABASE_URL', raising=False)
    monkeypatch.setenv('SCDS_PERSISTENCE_REQUIRED', 'true')
    monkeypatch.setenv('SCDS_PERSISTENCE_WRITE_ENABLED', 'false')
    monkeypatch.setenv('SCDS_REPOSITORY_API_KEY', 'test-repository-key')
    response = client.post('/repository/projects', headers={'x-scds-api-key': 'test-repository-key'}, json={'title': 'blocked'})
    assert response.status_code == 503
    assert response.json()['error'] == 'repository_unavailable'



def test_v340_repository_requires_scoped_auth(monkeypatch):
    monkeypatch.setenv('SCDS_REPOSITORY_API_KEY', 'test-repository-key')
    write = client.post('/repository/projects', json={'title': 'denied'})
    assert write.status_code == 403
    assert write.json()['required_scope'] == 'repository:write'
    read = client.get('/repository/decisions/example')
    assert read.status_code == 403
    assert read.json()['required_scope'] == 'repository:read'

def test_v340_route_inventory_preserves_v331_and_adds_repository_routes():
    current = json.loads((ROOT / 'data/backend_route_inventory_v3.4.0.json').read_text())
    previous = json.loads((ROOT / 'data/backend_route_inventory_v3.3.1.json').read_text())
    current_routes = {(r['path'], r['method']) for routes in current['routers'].values() for r in routes}
    previous_routes = {(r['path'], r['method']) for routes in previous['routers'].values() for r in routes}
    assert previous_routes <= current_routes
    assert current['route_count'] == 198
    assert len(current['routers']['repository']) == 13
