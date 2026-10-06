#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v3.4.0."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'wordpress-plugin' / 'sustainable-catalyst-decision-studio'
VERSION = '3.4.0'
BUILD = 'scds-v3.4.0-python-decision-repository-object-persistence'
SOURCE = 'release-v3.4.0'
REVISION = '0001_v330_pg_foundation'
REPOSITORY_SCHEMA = 'scds-python-decision-repository/1.0'


def req(value, message):
    if not value:
        raise AssertionError(message)


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def text(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


main = text('backend/app/main.py')
service = text('backend/app/services/decision_service.py')
persistence = text('backend/app/persistence/database.py')
models = text('backend/app/persistence/models.py')
repo = text('backend/app/persistence/repository.py')
contracts = text('backend/app/persistence/contracts.py')
migration = text('backend/migrations/versions/0001_v330_pg_foundation.py')
api_router = text('backend/app/api/router.py')
repository_routes = text('backend/app/api/routes/repository.py')
requirements = text('backend/requirements.txt')
php = (PLUGIN / 'sustainable-catalyst-decision-studio.php').read_text(encoding='utf-8')
readme = (PLUGIN / 'readme.txt').read_text(encoding='utf-8')
docker = text('backend/Dockerfile')
compose = text('compose.yml')
render = text('backend/render.yaml')
inv = load(ROOT / 'data/backend_route_inventory_v3.4.0.json')
previous = load(ROOT / 'data/backend_route_inventory_v3.3.1.json')
manifest = load(ROOT / 'data/decision_studio_release_manifest_v3.4.0.json')
pmanifest = load(PLUGIN / 'data/release_manifest_v3.4.0.json')
schema = load(ROOT / 'data/postgresql_schema_manifest_v3.4.0.json')
contract = load(ROOT / 'data/postgresql_persistence_contract_v3.4.0.json')
repo_contract = load(ROOT / 'data/python_decision_repository_contract_v3.4.0.json')

req('include_router(api_router)' in main, 'main composition router')
req('@app.get' not in main and '@app.post' not in main, 'main contains endpoint decorators')
req(len(main.splitlines()) <= 25, 'main is not composition-only')
req(f'APP_VERSION = "{VERSION}"' in service, 'service version')
req(BUILD in service and SOURCE in service, 'service identity')
req('REPOSITORY_SCHEMA' in service and 'PersistenceRepository' in service, 'repository service integration')
req('from app.api.routes.repository import router as repository_router' in api_router, 'repository router imported')
req('api_router.include_router(repository_router)' in api_router, 'repository router mounted')

route_dir = ROOT / 'backend/app/api/routes'
router_modules = sorted(p for p in route_dir.glob('*.py') if p.name != '__init__.py')
req(len(router_modules) == 14, f'expected 14 route registry modules, got {len(router_modules)}')
route_text = '\n'.join(p.read_text(encoding='utf-8') for p in router_modules)
for routes in inv['routers'].values():
    for route in routes:
        if route['path'].startswith('/v1/energy-runtime/'):
            continue
        req(repr(route['path']) in route_text, f"missing route {route['path']}")
req(inv['route_count'] == 198, 'v3.4 route count')
req(len(inv['routers']['repository']) == 13, 'repository route count')
old = {(r['path'], r['method']) for routes in previous['routers'].values() for r in routes}
new = {(r['path'], r['method']) for routes in inv['routers'].values() for r in routes}
req(old <= new, 'v3.3.1 routes not preserved')

req(manifest == pmanifest, 'release manifest parity')
req(manifest['release'] == VERSION and manifest['build_fingerprint'] == BUILD and manifest['source_commit'] == SOURCE, 'manifest identity')
req(manifest['backend']['route_count'] == 198 and manifest['backend']['route_registry_count'] == 14, 'manifest backend counts')
req(manifest['migration']['database_schema'] is False, 'v3.4 must not add a schema migration')
req(manifest['migration']['authority_cutover'] is True, 'authority cutover must be declared')
req(manifest['migration']['python_repository_authority'] is True, 'Python repository authority must move in v3.4')
req(manifest['migration']['wordpress_legacy_packet_storage_preserved'] is True, 'legacy WordPress source preservation')
req(manifest['decision_kernel']['final_decision_authority'] == 'human-governed', 'human decision authority')
req(manifest['repository']['schema'] == REPOSITORY_SCHEMA and manifest['repository']['authority'] == 'python-postgresql', 'repository manifest authority')

req(schema['revision'] == REVISION and schema['table_count'] == 20, 'schema manifest')
req(schema['authority'] == 'python-postgresql' and schema['live_write_authority'] is True, 'schema authority')
req(len(schema['tables']) == 20 and len(set(schema['tables'])) == 20, 'schema table inventory')
req(contract['database_schema_migration'] is False, 'persistence contract schema migration')
req(contract['postgresql_live_authority'] is True, 'PostgreSQL live authority')
req(contract['python_repository_live_authority'] is True, 'Python repository live authority')
req(contract['wordpress_decision_object_authority_changed'] is True, 'WordPress decision-object authority cutover')
req(contract['wordpress_legacy_packet_storage_preserved'] is True, 'WordPress compatibility preservation')
req(contract['v3_4_authority_cutover_complete'] is True, 'v3.4 cutover completion')
req(contract['final_decision_authority'] == 'human-governed', 'final human authority')

req(repo_contract['schema'] == REPOSITORY_SCHEMA and repo_contract['authority'] == 'python-postgresql', 'repository contract identity')
req(repo_contract['guarantees']['idempotent_legacy_object_import'] is True, 'idempotent import guarantee')
req(repo_contract['guarantees']['legacy_source_representation_preserved'] is True, 'legacy source preservation')
req(repo_contract['guarantees']['final_decision_authority'] == 'human-governed', 'repository human authority')
req(repo_contract['security']['repository_data_requires_api_key'] is True, 'repository authentication contract')
req(repo_contract['security']['read_scope'] == 'repository:read' and repo_contract['security']['write_scope'] == 'repository:write', 'repository scopes')
req(len(repo_contract['endpoints']) == 13, 'repository endpoint contract count')

for table in schema['tables']:
    req(f'__tablename__ = "{table}"' in models, f'model missing {table}')
    req(f'"{table}"' in migration, f'migration missing {table}')
req(REVISION in migration and REVISION in persistence, 'revision identity')
req(len(REVISION) <= 32, 'Alembic revision must fit default VARCHAR(32) version column')
req('PERSISTENCE_AUTHORITY = "python-postgresql"' in persistence, 'persistence authority constant')
req('postgresql_is_live_authority": True' in persistence, 'database authority contract')
req('v3_4_authority_cutover_complete": True' in persistence, 'authority cutover contract')
req('REPOSITORY_SCHEMA = "scds-python-decision-repository/1.0"' in contracts, 'repository schema contract')
req('class PersistenceRepository' in repo and 'live_write_authority": True' in repo, 'authoritative repository seam')
req('import_decision_object' in repo and 'decision_object.imported' in repo, 'legacy import support')
req('_repository_scope_error' in service and 'SCDS_REPOSITORY_API_KEY' in service, 'repository API authentication')
req('repository:read' in service and 'repository:write' in service, 'repository scoped authorization')
req('SCDS_REPOSITORY_API_KEY=' in text('.env.persistence-v330.example'), 'repository key example')
for endpoint in repo_contract['endpoints']:
    path = endpoint.split(' ', 1)[1]
    req(repr(path) in repository_routes, f'repository contract route missing {path}')
for dep in ['SQLAlchemy==2.0.36', 'psycopg[binary]==3.2.3', 'alembic==1.14.0']:
    req(dep in requirements, f'missing dependency {dep}')

req(' * Version: 3.4.0' in php and "const VERSION = '3.4.0';" in php, 'plugin release metadata')
req("const DB_VERSION = '3.0.0';" in php, 'WordPress DB version must remain 3.0.0')
req('Stable tag: 3.4.0' in readme, 'plugin stable tag')
for runtime in [docker, compose, render]:
    req(BUILD in runtime and SOURCE in runtime, 'runtime identity parity')
req('sustainable-catalyst-decision-studio:3.4.0' in compose, 'compose image version')
req('postgres:16-alpine' in compose and 'decision-studio-postgres-data' in compose, 'PostgreSQL compose foundation')
req('SCDS_PERSISTENCE_REQUIRED: "true"' in compose, 'production DB readiness gate')
req('SCDS_PERSISTENCE_WRITE_ENABLED: "true"' in compose, 'production repository writes enabled')
req("d.get('version') == '3.4.0'" in docker, 'Docker health version')
req('COPY migrations ./migrations' in docker and 'COPY alembic.ini ./alembic.ini' in docker, 'migration payload in image')

for path in [
    'data/backend_route_inventory_v3.3.1.json',
    'data/decision_studio_release_manifest_v3.3.1.json',
    'data/postgresql_schema_manifest_v3.3.1.json',
    'data/decision_module_registry_v3.2.0.json',
    'backend/app/decision_kernel.py',
    'backend/app/connected_decision_intelligence.py',
    'backend/app/recommendation_review.py',
]:
    req((ROOT / path).exists(), f'preserved {path}')

req('.venv-*/' in text('.gitignore') and '.venv/' in text('.gitignore'), 'virtualenv ignore rules')
tracked_venv = [p for p in ROOT.rglob('*') if p.is_file() and any(part.startswith('.venv') for part in p.relative_to(ROOT).parts)]
req(not tracked_venv, f'local virtualenv files present: {tracked_venv[:3]}')

jsons = [p for p in ROOT.rglob('*.json') if '.git' not in p.parts]
for p in jsons:
    load(p)
print(
    f'Decision Studio v{VERSION} release-integrity checks passed: authoritative Python/PostgreSQL repository, '
    f'13 repository routes, 20 persistence tables on Alembic revision {REVISION}, 14 route registries, '
    f'198 certified API routes, reversible legacy-object import, human-governed final decision authority, '
    f'and {len(jsons)} JSON files validated.'
)
