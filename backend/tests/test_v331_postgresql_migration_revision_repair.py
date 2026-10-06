from __future__ import annotations

import json
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.main import app
from app.persistence.database import (
    EXPECTED_SCHEMA_REVISION,
    PERSISTENCE_AUTHORITY,
    PERSISTENCE_TABLES,
    database_status,
    engine_for_url,
)

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


def test_v331_health_exposes_non_authoritative_persistence_foundation():
    body = client.get('/health').json()
    assert body['version'] == '3.3.1'
    assert body['persistence_schema'] == 'scds-postgresql-persistence/1.0'
    assert body['persistence_authority'] == PERSISTENCE_AUTHORITY
    assert body['release']['backend_architecture']['database_migration'] is True
    assert body['release']['backend_architecture']['postgresql_live_authority'] is False
    assert body['release']['backend_architecture']['wordpress_authority_change'] is False
    assert body['release']['persistence']['v3_4_authority_cutover_required'] is True


def test_persistence_contract_keeps_v33_non_authoritative():
    body = client.get('/persistence/contract').json()['persistence_contract']
    assert body['authority'] == 'non-authoritative-foundation'
    assert body['principles']['postgresql_is_live_authority'] is False
    assert body['principles']['writes_enabled_by_default'] is False
    assert body['principles']['v3_4_authority_cutover_required'] is True
    assert body['principles']['final_decision_authority'] == 'human-governed'
    assert len(body['tables']) == 20


def test_persistence_schema_manifest_has_expected_domain_tables():
    schema = client.get('/persistence/schema').json()['persistence_schema']
    expected = {
        'decision_projects','decisions','decision_objects','decision_modules','decision_module_bindings',
        'alternatives','criteria','criterion_values','assumptions','claims','evidence_links','scenarios',
        'scenario_variables','uncertainty_models','recommendations','reviews','challenges','decision_events',
        'artifacts','snapshots',
    }
    assert schema['revision'] == EXPECTED_SCHEMA_REVISION
    assert schema['table_count'] == 20
    assert set(schema['tables']) == expected == set(PERSISTENCE_TABLES)
    assert schema['module_registry_seed'] == ['canvas','finance','narrative-risk','global-impact']


def test_alembic_revision_identifier_fits_default_version_column():
    # Alembic's default version_num column is VARCHAR(32). This guards the production failure fixed in v3.3.1.
    assert len(EXPECTED_SCHEMA_REVISION) <= 32


def test_initial_alembic_migration_creates_schema_and_revision(tmp_path):
    db = tmp_path/'v331.sqlite3'
    url = f'sqlite:///{db}'
    cfg = Config(str(ROOT/'backend/alembic.ini'))
    cfg.set_main_option('script_location', str(ROOT/'backend/migrations'))
    cfg.set_main_option('sqlalchemy.url', url)
    command.upgrade(cfg, 'head')
    status = database_status(url)
    assert status['connected'] is True
    assert status['schema_revision'] == EXPECTED_SCHEMA_REVISION
    assert status['schema_current'] is True
    tables = set(inspect(engine_for_url(url)).get_table_names())
    assert set(PERSISTENCE_TABLES).issubset(tables)
    command.downgrade(cfg, 'base')


def test_v331_route_inventory_preserves_v320_and_adds_persistence_routes():
    current = json.loads((ROOT/'data/backend_route_inventory_v3.3.1.json').read_text())
    previous = json.loads((ROOT/'data/backend_route_inventory_v3.2.0.json').read_text())
    current_routes={(r['path'],r['method']) for routes in current['routers'].values() for r in routes}
    previous_routes={(r['path'],r['method']) for routes in previous['routers'].values() for r in routes}
    assert previous_routes <= current_routes
    assert current['route_count'] == 185
    assert len(current['routers']['persistence']) == 3
