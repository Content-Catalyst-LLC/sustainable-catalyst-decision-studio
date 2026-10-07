from __future__ import annotations

import json
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.main import app
from app.persistence.database import EXPECTED_SCHEMA_REVISION
from app.persistence.seed import seed_module_registry
from app.unified_module_registry import UNIFIED_DECISION_MODULE_REGISTRY_SCHEMA

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


def _db(monkeypatch, tmp_path):
    db = tmp_path / 'v390.sqlite3'
    url = f'sqlite:///{db}'
    cfg = Config(str(ROOT / 'backend/alembic.ini'))
    cfg.set_main_option('script_location', str(ROOT / 'backend/migrations'))
    cfg.set_main_option('sqlalchemy.url', url)
    command.upgrade(cfg, 'head')
    monkeypatch.setenv('SCDS_DATABASE_URL', url)
    monkeypatch.setenv('SCDS_PERSISTENCE_REQUIRED', 'true')
    monkeypatch.setenv('SCDS_PERSISTENCE_WRITE_ENABLED', 'true')
    seed_module_registry()
    return url


def test_v390_release_and_health_publish_unified_registry_schema():
    health = client.get('/health').json()
    assert health['version'] == '3.9.0'
    assert health['unified_decision_module_registry_schema'] == UNIFIED_DECISION_MODULE_REGISTRY_SCHEMA
    release = client.get('/release').json()['release']
    assert release['release_name'] == 'Unified Decision Module Registry'
    assert release['build_fingerprint'] == 'scds-v3.9.0-unified-decision-module-registry'
    assert release['backend_architecture']['database_migration'] is False
    assert release['backend_architecture']['unified_decision_module_registry'] is True
    assert release['backend_architecture']['unified_registry_canonical'] is True
    assert release['backend_architecture']['legacy_module_registry_endpoints_preserved'] is True
    assert release['unified_module_registry']['schema'] == UNIFIED_DECISION_MODULE_REGISTRY_SCHEMA
    assert release['unified_module_registry']['module_count'] == 4


def test_v390_registry_unifies_all_four_authoritative_modules():
    body = client.get('/decision-module-registry').json()
    assert body['ok'] is True
    registry = body['registry']
    assert registry['schema'] == UNIFIED_DECISION_MODULE_REGISTRY_SCHEMA
    assert registry['module_count'] == 4
    assert registry['registry_authority'] == 'decision-studio-kernel'
    assert registry['registry_role'] == 'canonical-module-discovery-and-readiness-control-plane'
    assert registry['compatibility']['legacy_decision_modules_endpoints_preserved'] is True
    assert registry['governance']['registry_does_not_auto_recommend'] is True
    assert registry['governance']['final_decision_authority'] == 'human-governed'
    modules = {m['module_id']: m for m in registry['modules']}
    assert set(modules) == {'canvas', 'finance', 'narrative-risk', 'global-impact'}
    for module in modules.values():
        assert module['status'] == 'python-domain-authoritative'
        assert module['authority']['storage'] == 'python-postgresql'
        assert module['security']['read_scope']
        assert module['security']['write_scope']
        assert module['schemas']['domain'].startswith('scds-')
    assert modules['finance']['authority']['compute'] == 'workbench'
    assert modules['global-impact']['authority']['compute'] == 'workbench'
    assert modules['canvas']['authority']['compute'] is None
    assert modules['narrative-risk']['authority']['compute'] is None


def test_v390_registry_indexes_capabilities_and_providers():
    caps = client.get('/decision-module-registry/capabilities').json()['capability_index']
    assert caps['schema'] == UNIFIED_DECISION_MODULE_REGISTRY_SCHEMA
    lookup = {x['capability']: x['modules'] for x in caps['capabilities']}
    assert lookup['criteria-and-alternatives'] == ['canvas']
    assert lookup['financial-scenarios'] == ['finance']
    assert lookup['contradiction-tracing'] == ['narrative-risk']
    assert lookup['sdg-alignment'] == ['global-impact']

    providers = client.get('/decision-module-registry/providers').json()['provider_index']
    pmap = {x['provider']: x for x in providers['providers']}
    assert sorted(pmap['workbench']['modules']) == ['canvas', 'finance', 'global-impact']
    assert 'compute_authority' in pmap['workbench']['roles']
    assert 'knowledge-library' in pmap
    assert 'site-intelligence' in pmap


def test_v390_registry_module_lookup_and_legacy_compatibility():
    for module_id in ('canvas', 'finance', 'narrative-risk', 'global-impact'):
        unified = client.get(f'/decision-module-registry/modules/{module_id}')
        assert unified.status_code == 200
        module = unified.json()['module']
        legacy = client.get(f'/decision-modules/{module_id}')
        assert legacy.status_code == 200
        assert module['module_id'] == legacy.json()['contract']['module_id']
        assert module['schemas']['domain'] == legacy.json()['contract']['domain_schema']
    missing = client.get('/decision-module-registry/modules/not-a-module')
    assert missing.status_code == 404
    assert missing.json()['error'] == 'unknown_module'


def test_v390_registry_validation_detects_missing_or_unknown_modules():
    registry = client.get('/decision-module-registry').json()['registry']
    ok = client.post('/decision-module-registry/validate', json={'registry': registry, 'strict': True})
    assert ok.status_code == 200
    assert ok.json()['ok'] is True

    missing = dict(registry)
    missing['modules'] = registry['modules'][:-1]
    missing['module_count'] = 3
    bad = client.post('/decision-module-registry/validate', json={'registry': missing, 'strict': True})
    assert bad.status_code == 200
    assert bad.json()['ok'] is False
    assert any(e.startswith('missing_modules:') for e in bad.json()['errors'])


def test_v390_registry_readiness_tracks_persistence(monkeypatch, tmp_path):
    _db(monkeypatch, tmp_path)
    readiness = client.get('/decision-module-registry/readiness').json()['readiness']
    assert readiness['ready'] is True
    assert readiness['module_count'] == 4
    assert readiness['authoritative_module_count'] == 4
    assert readiness['all_modules_authoritative'] is True
    assert readiness['persistence_ready'] is True
    assert readiness['storage_authority'] == 'python-postgresql'
    assert readiness['compute_authorities'] == {'finance': 'workbench', 'global-impact': 'workbench'}
    assert readiness['final_decision_authority'] == 'human-governed'


def test_v390_route_inventory_preserves_v380_and_adds_registry_routes():
    current = json.loads((ROOT / 'data/backend_route_inventory_v3.9.0.json').read_text())
    previous = json.loads((ROOT / 'data/backend_route_inventory_v3.8.0.json').read_text())
    current_routes = {(r['path'], r['method']) for routes in current['routers'].values() for r in routes}
    previous_routes = {(r['path'], r['method']) for routes in previous['routers'].values() for r in routes}
    assert previous_routes <= current_routes
    assert current['route_count'] == 249
    assert len(current['routers']['module_registry']) == 7
    expected = {
        ('GET', '/decision-module-registry'),
        ('GET', '/decision-module-registry/modules'),
        ('GET', '/decision-module-registry/modules/{module_id}'),
        ('GET', '/decision-module-registry/capabilities'),
        ('GET', '/decision-module-registry/providers'),
        ('GET', '/decision-module-registry/readiness'),
        ('POST', '/decision-module-registry/validate'),
    }
    assert expected <= {(r['method'], r['path']) for r in current['routers']['module_registry']}


def test_v390_schema_revision_is_unchanged():
    assert EXPECTED_SCHEMA_REVISION == '0001_v330_pg_foundation'
