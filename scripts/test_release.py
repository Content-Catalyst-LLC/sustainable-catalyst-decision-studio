#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v3.5.0."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'wordpress-plugin' / 'sustainable-catalyst-decision-studio'
VERSION = '3.5.0'
BUILD = 'scds-v3.5.0-canvas-python-domain-migration'
SOURCE = 'release-v3.5.0'
REVISION = '0001_v330_pg_foundation'
REPOSITORY_SCHEMA = 'scds-python-decision-repository/1.0'
CANVAS_SCHEMA = 'scds-canvas-domain/1.0'


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
canvas = text('backend/app/domains/canvas.py')
kernel = text('backend/app/decision_kernel.py')
migration = text('backend/migrations/versions/0001_v330_pg_foundation.py')
api_router = text('backend/app/api/router.py')
canvas_routes = text('backend/app/api/routes/canvas.py')
requirements = text('backend/requirements.txt')
php = (PLUGIN / 'sustainable-catalyst-decision-studio.php').read_text(encoding='utf-8')
readme = (PLUGIN / 'readme.txt').read_text(encoding='utf-8')
docker = text('backend/Dockerfile')
compose = text('compose.yml')
render = text('backend/render.yaml')
inv = load(ROOT / 'data/backend_route_inventory_v3.5.0.json')
previous = load(ROOT / 'data/backend_route_inventory_v3.4.0.json')
manifest = load(ROOT / 'data/decision_studio_release_manifest_v3.5.0.json')
pmanifest = load(PLUGIN / 'data/release_manifest_v3.5.0.json')
schema = load(ROOT / 'data/postgresql_schema_manifest_v3.5.0.json')
contract = load(ROOT / 'data/postgresql_persistence_contract_v3.5.0.json')
canvas_contract = load(ROOT / 'data/canvas_python_domain_contract_v3.5.0.json')

req('include_router(api_router)' in main, 'main composition router')
req('@app.get' not in main and '@app.post' not in main, 'main contains endpoint decorators')
req(len(main.splitlines()) <= 25, 'main is not composition-only')
req(f'APP_VERSION = "{VERSION}"' in service, 'service version')
req(BUILD in service and SOURCE in service, 'service identity')
req('CANVAS_DOMAIN_SCHEMA' in service and 'CanvasDomainRepository' in service, 'Canvas service integration')
req('from app.api.routes.canvas import router as canvas_router' in api_router, 'Canvas router imported')
req('api_router.include_router(canvas_router)' in api_router, 'Canvas router mounted')

route_dir = ROOT / 'backend/app/api/routes'
router_modules = sorted(p for p in route_dir.glob('*.py') if p.name != '__init__.py')
req(len(router_modules) == 15, f'expected 15 route registry modules, got {len(router_modules)}')
route_text = '\n'.join(p.read_text(encoding='utf-8') for p in router_modules)
for routes in inv['routers'].values():
    for route in routes:
        if route['path'].startswith('/v1/energy-runtime/'):
            continue
        req(repr(route['path']) in route_text, f"missing route {route['path']}")
req(inv['route_count'] == 209, 'v3.5 route count')
req(len(inv['routers']['canvas']) == 11, 'Canvas route count')
old = {(r['path'], r['method']) for routes in previous['routers'].values() for r in routes}
new = {(r['path'], r['method']) for routes in inv['routers'].values() for r in routes}
req(old <= new, 'v3.4 routes not preserved')

req(manifest == pmanifest, 'release manifest parity')
req(manifest['release'] == VERSION and manifest['build_fingerprint'] == BUILD and manifest['source_commit'] == SOURCE, 'manifest identity')
req(manifest['backend']['route_count'] == 209 and manifest['backend']['route_registry_count'] == 15, 'manifest backend counts')
req(manifest['migration']['database_schema'] is False, 'v3.5 must not add a schema migration')
req(manifest['migration']['authority_cutover'] is False, 'v3.5 must not repeat the v3.4 repository authority cutover')
req(manifest['migration']['canvas_python_domain_authority'] is True, 'Canvas domain authority migration')
req(manifest['migration']['canvas_wordpress_domain_authority_changed'] is True, 'Canvas WordPress domain authority change')
req(manifest['decision_kernel']['final_decision_authority'] == 'human-governed', 'human decision authority')
req(manifest['repository']['authority'] == 'python-postgresql', 'repository authority preserved')
req(manifest['canvas']['schema'] == CANVAS_SCHEMA and manifest['canvas']['status'] == 'python-domain-authoritative', 'Canvas manifest identity')
req(manifest['next_release'].startswith('3.6.0'), 'next release')

req(schema['revision'] == REVISION and schema['table_count'] == 20, 'schema manifest')
req(schema['authority'] == 'python-postgresql' and schema['live_write_authority'] is True, 'schema authority')
req(schema['canvas_domain_schema'] == CANVAS_SCHEMA and schema['canvas_python_domain_authoritative'] is True, 'Canvas schema annotation')
req(len(schema['tables']) == 20 and len(set(schema['tables'])) == 20, 'schema table inventory')
req(contract['database_schema_migration'] is False, 'persistence contract schema migration')
req(contract['postgresql_live_authority'] is True and contract['python_repository_live_authority'] is True, 'repository authority preserved')
req(contract['canvas_domain_schema'] == CANVAS_SCHEMA and contract['canvas_python_domain_authoritative'] is True, 'Canvas persistence contract')
req(contract['new_schema_migration_in_v3_5'] is False, 'no v3.5 schema migration')
req(contract['final_decision_authority'] == 'human-governed', 'final human authority')

req(canvas_contract['schema'] == CANVAS_SCHEMA and canvas_contract['status'] == 'python-domain-authoritative', 'Canvas contract identity')
req(canvas_contract['storage_authority'] == 'python-postgresql', 'Canvas storage authority')
req(canvas_contract['security']['read_scope'] == 'canvas:read' and canvas_contract['security']['write_scope'] == 'canvas:write', 'Canvas scopes')
req(canvas_contract['compatibility']['legacy_catalyst_canvas_import'] is True, 'legacy Canvas import')
req(canvas_contract['compatibility']['legacy_wordpress_source_preserved'] is True, 'legacy Canvas source preservation')
req(canvas_contract['boundaries']['shared_decision_identity_owned_by_kernel'] is True, 'Kernel decision identity')
req(canvas_contract['boundaries']['automatic_winner_selection'] is False, 'no auto winner')
req(canvas_contract['boundaries']['automatic_recommendation'] is False, 'no auto recommendation')
req(canvas_contract['boundaries']['final_decision_authority'] == 'human-governed', 'Canvas human authority')
req(len(canvas_contract['endpoints']) == 11, 'Canvas endpoint contract count')
for endpoint in canvas_contract['endpoints']:
    path = endpoint.split(' ', 1)[1]
    req(repr(path) in canvas_routes, f'Canvas contract route missing {path}')

req('CANVAS_DOMAIN_SCHEMA = "scds-canvas-domain/1.0"' in canvas, 'Canvas domain schema constant')
req('class CanvasDomainRepository' in canvas, 'Canvas repository class')
req('replace_alternatives' in canvas and 'replace_criteria' in canvas and 'replace_assumptions' in canvas, 'Canvas normalized relational writers')
req('object_type == CANVAS_OBJECT_TYPE' in canvas, 'Canvas canonical domain object')
req('legacy_artifact' in canvas and 'canvas.legacy_imported' in canvas, 'source-preserving legacy import')
req('automatic_winner_selection": False' in canvas and 'automatic_recommendation": False' in canvas, 'Canvas automation boundaries')
req('"status": "python-domain-authoritative"' in kernel, 'Canvas module runtime status')
req('"persistence_authority": "python-postgresql"' in kernel, 'Canvas module persistence provider')
req('_canvas_scope_error' in service and 'canvas:read' in service and 'canvas:write' in service, 'Canvas scoped authorization')

for table in schema['tables']:
    req(f'__tablename__ = "{table}"' in models, f'model missing {table}')
    req(f'"{table}"' in migration, f'migration missing {table}')
req(REVISION in migration and REVISION in persistence, 'revision identity')
req(len(REVISION) <= 32, 'Alembic revision must fit default VARCHAR(32) version column')
req('PERSISTENCE_AUTHORITY = "python-postgresql"' in persistence, 'persistence authority constant')
req('class PersistenceRepository' in repo, 'authoritative repository preserved')
for dep in ['SQLAlchemy==2.0.36', 'psycopg[binary]==3.2.3', 'alembic==1.14.0']:
    req(dep in requirements, f'missing dependency {dep}')

req(' * Version: 3.5.0' in php and "const VERSION = '3.5.0';" in php, 'plugin release metadata')
req("const DB_VERSION = '3.0.0';" in php, 'WordPress DB version must remain 3.0.0')
req('Stable tag: 3.5.0' in readme, 'plugin stable tag')
req(BUILD in php and SOURCE in php, 'plugin build identity')
req('sustainable-catalyst-decision-studio:3.5.0' in compose, 'compose image version')
req('SCDS_PERSISTENCE_REQUIRED: "true"' in compose, 'production DB readiness gate')
req('SCDS_PERSISTENCE_WRITE_ENABLED: "true"' in compose, 'repository writes preserved')
req("d.get('version') == '3.5.0'" in docker, 'Docker health version')
req('COPY migrations ./migrations' in docker and 'COPY alembic.ini ./alembic.ini' in docker, 'migration payload in image')
req(BUILD in render and SOURCE in render, 'render release identity')

for path in [
    'data/backend_route_inventory_v3.4.0.json',
    'data/decision_studio_release_manifest_v3.4.0.json',
    'data/postgresql_schema_manifest_v3.4.0.json',
    'data/python_decision_repository_contract_v3.4.0.json',
    'data/canvas_module_contract_v3.2.0.json',
    'backend/app/persistence/repository.py',
    'backend/app/decision_kernel.py',
]:
    req((ROOT / path).exists(), f'preserved {path}')

req('.venv-*/' in text('.gitignore') and '.venv/' in text('.gitignore'), 'virtualenv ignore rules')
tracked_venv = [p for p in ROOT.rglob('*') if p.is_file() and any(part.startswith('.venv') for part in p.relative_to(ROOT).parts)]
req(not tracked_venv, f'local virtualenv files present: {tracked_venv[:3]}')

jsons = [p for p in ROOT.rglob('*.json') if '.git' not in p.parts]
for p in jsons:
    load(p)
print(
    f'Decision Studio v{VERSION} release-integrity checks passed: Canvas Python domain authority, '
    f'11 Canvas routes, 20 persistence tables on preserved Alembic revision {REVISION}, 15 route registries, '
    f'209 certified API routes, source-preserving legacy Catalyst Canvas import, human-governed final decision authority, '
    f'and {len(jsons)} JSON files validated.'
)
