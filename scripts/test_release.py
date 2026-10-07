#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v3.6.0."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'wordpress-plugin' / 'sustainable-catalyst-decision-studio'
VERSION = '3.6.0'
BUILD = 'scds-v3.6.0-finance-python-domain-migration'
SOURCE = 'release-v3.6.0'
REVISION = '0001_v330_pg_foundation'
REPOSITORY_SCHEMA = 'scds-python-decision-repository/1.0'
CANVAS_SCHEMA = 'scds-canvas-domain/1.0'
FINANCE_SCHEMA = 'scds-finance-domain/1.0'


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
finance = text('backend/app/domains/finance.py')
kernel = text('backend/app/decision_kernel.py')
migration = text('backend/migrations/versions/0001_v330_pg_foundation.py')
api_router = text('backend/app/api/router.py')
finance_routes = text('backend/app/api/routes/finance.py')
requirements = text('backend/requirements.txt')
php = (PLUGIN / 'sustainable-catalyst-decision-studio.php').read_text(encoding='utf-8')
readme = (PLUGIN / 'readme.txt').read_text(encoding='utf-8')
docker = text('backend/Dockerfile')
compose = text('compose.yml')
render = text('backend/render.yaml')
inv = load(ROOT / 'data/backend_route_inventory_v3.6.0.json')
previous = load(ROOT / 'data/backend_route_inventory_v3.5.0.json')
manifest = load(ROOT / 'data/decision_studio_release_manifest_v3.6.0.json')
pmanifest = load(PLUGIN / 'data/release_manifest_v3.6.0.json')
schema = load(ROOT / 'data/postgresql_schema_manifest_v3.6.0.json')
contract = load(ROOT / 'data/postgresql_persistence_contract_v3.6.0.json')
finance_contract = load(ROOT / 'data/finance_python_domain_contract_v3.6.0.json')

req('include_router(api_router)' in main, 'main composition router')
req('@app.get' not in main and '@app.post' not in main, 'main contains endpoint decorators')
req(len(main.splitlines()) <= 25, 'main is not composition-only')
req(f'APP_VERSION = "{VERSION}"' in service, 'service version')
req(BUILD in service and SOURCE in service, 'service identity')
req('FINANCE_DOMAIN_SCHEMA' in service and 'FinanceDomainRepository' in service, 'Finance service integration')
req('from app.api.routes.finance import router as finance_router' in api_router, 'Finance router imported')
req('api_router.include_router(finance_router)' in api_router, 'Finance router mounted')

route_dir = ROOT / 'backend/app/api/routes'
router_modules = sorted(p for p in route_dir.glob('*.py') if p.name != '__init__.py')
req(len(router_modules) == 16, f'expected 16 route registry modules, got {len(router_modules)}')
route_text = '\n'.join(p.read_text(encoding='utf-8') for p in router_modules)
for routes in inv['routers'].values():
    for route in routes:
        if route['path'].startswith('/v1/energy-runtime/'):
            continue
        req(repr(route['path']) in route_text, f"missing route {route['path']}")
req(inv['route_count'] == 220, 'v3.6 route count')
req(len(inv['routers']['finance']) == 11, 'Finance route count')
old = {(r['path'], r['method']) for routes in previous['routers'].values() for r in routes}
new = {(r['path'], r['method']) for routes in inv['routers'].values() for r in routes}
req(old <= new, 'v3.5 routes not preserved')

req(manifest == pmanifest, 'release manifest parity')
req(manifest['release'] == VERSION and manifest['build_fingerprint'] == BUILD and manifest['source_commit'] == SOURCE, 'manifest identity')
req(manifest['backend']['route_count'] == 220 and manifest['backend']['route_registry_count'] == 16, 'manifest backend counts')
req(manifest['migration']['database_schema'] is False, 'v3.6 must not add a schema migration')
req(manifest['migration']['authority_cutover'] is False, 'v3.6 must not repeat repository authority cutover')
req(manifest['migration']['finance_python_domain_authority'] is True, 'Finance domain authority migration')
req(manifest['decision_kernel']['canvas_python_domain_authoritative'] is True, 'Canvas authority preserved')
req(manifest['decision_kernel']['finance_python_domain_authoritative'] is True, 'Finance authority')
req(manifest['decision_kernel']['finance_compute_authority'] == 'workbench', 'Workbench finance compute authority')
req(manifest['decision_kernel']['final_decision_authority'] == 'human-governed', 'human decision authority')
req(manifest['repository']['authority'] == 'python-postgresql', 'repository authority preserved')
req(manifest['finance']['schema'] == FINANCE_SCHEMA and manifest['finance']['status'] == 'python-domain-authoritative', 'Finance manifest identity')
req(manifest['finance']['compute_authority'] == 'workbench', 'Finance compute authority')
req(manifest['next_release'].startswith('3.7.0'), 'next release')

req(schema['revision'] == REVISION and schema['table_count'] == 20, 'schema manifest')
req(schema['authority'] == 'python-postgresql' and schema['live_write_authority'] is True, 'schema authority')
req(schema['canvas_python_domain_authoritative'] is True, 'Canvas schema annotation')
req(schema['finance_domain_schema'] == FINANCE_SCHEMA and schema['finance_python_domain_authoritative'] is True, 'Finance schema annotation')
req(schema['finance_compute_authority'] == 'workbench', 'Finance compute authority annotation')
req(len(schema['tables']) == 20 and len(set(schema['tables'])) == 20, 'schema table inventory')
req(contract['database_schema_migration'] is False, 'persistence contract schema migration')
req(contract['postgresql_live_authority'] is True and contract['python_repository_live_authority'] is True, 'repository authority preserved')
req(contract['finance_domain_schema'] == FINANCE_SCHEMA and contract['finance_python_domain_authoritative'] is True, 'Finance persistence contract')
req(contract['new_schema_migration_in_v3_6'] is False, 'no v3.6 schema migration')
req(contract['finance_compute_authority'] == 'workbench', 'Finance persistence compute authority')
req(contract['final_decision_authority'] == 'human-governed', 'final human authority')

req(finance_contract['schema'] == FINANCE_SCHEMA and finance_contract['status'] == 'python-domain-authoritative', 'Finance contract identity')
req(finance_contract['storage_authority'] == 'python-postgresql', 'Finance storage authority')
req(finance_contract['compute_authority'] == 'workbench', 'Finance contract compute authority')
req(finance_contract['security']['read_scope'] == 'finance:read' and finance_contract['security']['write_scope'] == 'finance:write', 'Finance scopes')
req(finance_contract['compatibility']['legacy_catalyst_finance_import'] is True, 'legacy Finance import')
req(finance_contract['compatibility']['legacy_wordpress_source_preserved'] is True, 'legacy Finance source preservation')
req(finance_contract['boundaries']['shared_decision_identity_owned_by_kernel'] is True, 'Kernel decision identity')
req(finance_contract['boundaries']['workbench_is_compute_authority'] is True, 'Workbench authority boundary')
req(finance_contract['boundaries']['decision_studio_executes_financial_models'] is False, 'Decision Studio must not execute finance models')
req(finance_contract['boundaries']['model_output_is_automatic_recommendation'] is False, 'no auto recommendation')
req(finance_contract['boundaries']['financial_score_is_final_decision_authority'] is False, 'no finance score authority')
req(finance_contract['boundaries']['final_decision_authority'] == 'human-governed', 'Finance human authority')
req(len(finance_contract['endpoints']) == 11, 'Finance endpoint contract count')
for endpoint in finance_contract['endpoints']:
    path = endpoint.split(' ', 1)[1]
    req(repr(path) in finance_routes, f'Finance contract route missing {path}')

req('FINANCE_DOMAIN_SCHEMA = "scds-finance-domain/1.0"' in finance, 'Finance domain schema constant')
req('class FinanceDomainRepository' in finance, 'Finance repository class')
for method in ['replace_assumptions', 'replace_scenarios', 'replace_uncertainty_models', 'replace_workbench_receipts']:
    req(method in finance, f'Finance relational writer missing {method}')
req('FINANCE_RECEIPT_ARTIFACT_TYPE = "finance-workbench-receipt"' in finance, 'Workbench receipt type')
req('"compute_authority": "workbench"' in finance, 'Workbench compute boundary')
req('decision_studio_executes_financial_models": False' in finance, 'no finance runtime execution')
req('legacy_artifact' in finance and 'finance.legacy_imported' in finance, 'source-preserving legacy Finance import')
req('_finance_scope_error' in service and 'finance:read' in service and 'finance:write' in service, 'Finance scoped authorization')
req('_canvas_owned_assumption' in canvas and '"domain": "canvas"' in canvas, 'Canvas domain ownership isolation')
req('"domain": FINANCE_DOMAIN_MARKER' in finance, 'Finance domain ownership metadata')
req('"status": "python-domain-authoritative"' in kernel, 'module runtime status')
req('"compute_authority": "workbench"' in kernel, 'Finance module compute provider')

for table in schema['tables']:
    req(f'__tablename__ = "{table}"' in models, f'model missing {table}')
    req(f'"{table}"' in migration, f'migration missing {table}')
req(REVISION in migration and REVISION in persistence, 'revision identity')
req(len(REVISION) <= 32, 'Alembic revision must fit default VARCHAR(32) version column')
req('PERSISTENCE_AUTHORITY = "python-postgresql"' in persistence, 'persistence authority constant')
req('class PersistenceRepository' in repo, 'authoritative repository preserved')
for dep in ['SQLAlchemy==2.0.36', 'psycopg[binary]==3.2.3', 'alembic==1.14.0']:
    req(dep in requirements, f'missing dependency {dep}')

req(' * Version: 3.6.0' in php and "const VERSION = '3.6.0';" in php, 'plugin release metadata')
req("const DB_VERSION = '3.0.0';" in php, 'WordPress DB version must remain 3.0.0')
req('Stable tag: 3.6.0' in readme, 'plugin stable tag')
req(BUILD in php and SOURCE in php, 'plugin build identity')
req('sustainable-catalyst-decision-studio:3.6.0' in compose, 'compose image version')
req('SCDS_PERSISTENCE_REQUIRED: "true"' in compose, 'production DB readiness gate')
req('SCDS_PERSISTENCE_WRITE_ENABLED: "true"' in compose, 'repository writes preserved')
req("d.get('version') == '3.6.0'" in docker, 'Docker health version')
req('COPY migrations ./migrations' in docker and 'COPY alembic.ini ./alembic.ini' in docker, 'migration payload in image')
req(BUILD in render and SOURCE in render, 'render release identity')

for path in [
    'data/backend_route_inventory_v3.5.0.json',
    'data/decision_studio_release_manifest_v3.5.0.json',
    'data/postgresql_schema_manifest_v3.5.0.json',
    'data/canvas_python_domain_contract_v3.5.0.json',
    'data/python_decision_repository_contract_v3.4.0.json',
    'backend/app/domains/canvas.py',
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
    f'Decision Studio v{VERSION} release-integrity checks passed: Finance Python domain authority with Workbench compute boundary, '
    f'11 Finance routes, Canvas/Finance shared-table ownership isolation, 20 persistence tables on preserved Alembic revision {REVISION}, '
    f'16 route registries, 220 certified API routes, source-preserving legacy Catalyst Finance import, human-governed final decision authority, '
    f'and {len(jsons)} JSON files validated.'
)
