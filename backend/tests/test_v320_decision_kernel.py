import json
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.decision_kernel import (
    DECISION_KERNEL_SCHEMA,
    DECISION_MODULE_CONTRACT_SCHEMA,
    KERNEL_OBJECTS,
    module_registry,
)

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


def test_v320_release_identity_and_migration_boundary():
    health = client.get('/health').json()
    assert health['version'] == '3.12.0'
    assert health['decision_kernel_schema'] == DECISION_KERNEL_SCHEMA
    assert health['registered_decision_modules'] == 4
    release = client.get('/release').json()['release']
    assert release['release_name'] == 'Module Interoperability & Shared Evidence'
    assert release['build_fingerprint'] == 'scds-v3.12.0-module-interoperability-shared-evidence'
    assert release['decision_kernel']['module_count'] == 4
    assert release['decision_kernel']['database_migration'] is False
    assert release['decision_kernel']['wordpress_decision_object_authority_change'] is True
    assert release['decision_kernel']['final_decision_authority'] == 'human-governed'


def test_module_registry_has_four_first_class_modules():
    response = client.get('/decision-modules')
    assert response.status_code == 200
    registry = response.json()['registry']
    assert registry['module_count'] == 4
    ids = {m['module_id'] for m in registry['modules']}
    assert ids == {'canvas', 'finance', 'narrative-risk', 'global-impact'}
    finance = next(m for m in registry['modules'] if m['module_id'] == 'finance')
    assert finance['providers']['compute_authority'] == 'workbench'
    assert 'decision-studio-does-not-duplicate-workbench-calculation-runtime' in finance['boundaries']


def test_registered_module_contracts_extend_only_kernel_objects():
    known = set(KERNEL_OBJECTS)
    for module in module_registry()['modules']:
        assert module['module_contract_schema'] == DECISION_MODULE_CONTRACT_SCHEMA
        assert set(module['extends_kernel_objects']) <= known
        response = client.get(f"/decision-modules/{module['module_id']}")
        assert response.status_code == 200
        assert response.json()['contract']['module_id'] == module['module_id']


def test_kernel_template_and_validation():
    template = client.get('/decision-kernel/template').json()['kernel']
    assert template['schema'] == DECISION_KERNEL_SCHEMA
    template['decision']['decision_id'] = 'decision-001'
    template['decision']['decision_question'] = 'Which option should the governed review process advance?'
    response = client.post('/decision-kernel/validate', json={'kernel': template, 'strict': True})
    assert response.status_code == 200
    body = response.json()
    assert body['ok'] is True
    assert body['module_ids'] == ['canvas']
    assert body['normalized_kernel']['authorities']['final_decision_authority'] == 'human-governed'


def test_kernel_rejects_unknown_module_and_authority_override():
    payload = {
        'schema': DECISION_KERNEL_SCHEMA,
        'decision': {'decision_id': 'd-2', 'decision_question': 'Test?'},
        'module_bindings': [{'module_id': 'unknown'}],
        'authorities': {'final_decision_authority': 'model'},
    }
    body = client.post('/decision-kernel/validate', json={'kernel': payload}).json()
    assert body['ok'] is False
    assert any(x.startswith('unknown_module_binding') for x in body['errors'])
    assert 'final_decision_authority_must_remain_human_governed' in body['errors']


def test_module_contract_validation_blocks_kernel_object_and_authority_mutation():
    ok = client.post('/decision-modules/global-impact/validate', json={'contract': {
        'module_id': 'global-impact',
        'extends_kernel_objects': ['decision', 'criterion', 'outcome'],
    }}).json()
    assert ok['ok'] is True
    bad = client.post('/decision-modules/finance/validate', json={'contract': {
        'module_id': 'finance',
        'extends_kernel_objects': ['decision', 'invented-object'],
        'final_decision_authority': 'model',
    }}).json()
    assert bad['ok'] is False
    assert 'module_cannot_override_final_decision_authority' in bad['errors']


def test_v320_route_inventory_includes_kernel_routes_and_preserves_v310_routes():
    current = json.loads((ROOT/'data/backend_route_inventory_v3.2.0.json').read_text())
    previous = json.loads((ROOT/'data/backend_route_inventory_v3.1.0.json').read_text())
    current_routes={(r['path'],r['method']) for routes in current['routers'].values() for r in routes}
    previous_routes={(r['path'],r['method']) for routes in previous['routers'].values() for r in routes}
    assert previous_routes <= current_routes
    assert current['route_count'] == 182
    assert len(current['routers']['decision_kernel']) == 6
