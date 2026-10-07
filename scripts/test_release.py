#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v3.9.0."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'wordpress-plugin' / 'sustainable-catalyst-decision-studio'
VERSION = '3.9.0'
BUILD = 'scds-v3.9.0-unified-decision-module-registry'
SOURCE = 'release-v3.9.0'
REVISION = '0001_v330_pg_foundation'
REGISTRY_SCHEMA = 'scds-unified-decision-module-registry/1.0'
MODULE_IDS = {'canvas', 'finance', 'narrative-risk', 'global-impact'}


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
registry_py = text('backend/app/unified_module_registry.py')
api_router = text('backend/app/api/router.py')
registry_routes = text('backend/app/api/routes/module_registry.py')
persistence = text('backend/app/persistence/database.py')
models = text('backend/app/persistence/models.py')
migration = text('backend/migrations/versions/0001_v330_pg_foundation.py')
requirements = text('backend/requirements.txt')
php = (PLUGIN / 'sustainable-catalyst-decision-studio.php').read_text(encoding='utf-8')
readme = (PLUGIN / 'readme.txt').read_text(encoding='utf-8')
docker = text('backend/Dockerfile')
compose = text('compose.yml')
render = text('backend/render.yaml')
inv = load(ROOT / 'data/backend_route_inventory_v3.9.0.json')
previous = load(ROOT / 'data/backend_route_inventory_v3.8.0.json')
manifest = load(ROOT / 'data/decision_studio_release_manifest_v3.9.0.json')
pmanifest = load(PLUGIN / 'data/release_manifest_v3.9.0.json')
schema = load(ROOT / 'data/postgresql_schema_manifest_v3.9.0.json')
contract = load(ROOT / 'data/postgresql_persistence_contract_v3.9.0.json')
registry_contract = load(ROOT / 'data/unified_decision_module_registry_contract_v3.9.0.json')

req('from app.api.router import api_router' in main and 'app.include_router(api_router)' in main, 'composition router')
req('@app.get' not in main and '@app.post' not in main, 'main contains endpoint decorators')
req(f'APP_VERSION = "{VERSION}"' in service, 'service version')
req(BUILD in service and SOURCE in service, 'service identity')
req('UNIFIED_DECISION_MODULE_REGISTRY_SCHEMA' in service, 'registry service integration')
req('from app.api.routes.module_registry import router as module_registry_router' in api_router, 'registry router imported')
req('api_router.include_router(module_registry_router)' in api_router, 'registry router mounted')
req(f'UNIFIED_DECISION_MODULE_REGISTRY_SCHEMA = "{REGISTRY_SCHEMA}"' in registry_py, 'registry schema constant')

route_dir = ROOT / 'backend/app/api/routes'
router_modules = sorted(p for p in route_dir.glob('*.py') if p.name != '__init__.py')
req(len(router_modules) == 19, f'expected 19 route registry modules, got {len(router_modules)}')
route_text = '\n'.join(p.read_text(encoding='utf-8') for p in router_modules)
for routes in inv['routers'].values():
    for route in routes:
        if route['path'].startswith('/v1/energy-runtime/'):
            continue
        req(repr(route['path']) in route_text, f"missing route {route['path']}")
req(inv['route_count'] == 249, 'v3.9 route count')
req(len(inv['routers']['module_registry']) == 7, 'unified registry route count')
old = {(r['path'], r['method']) for routes in previous['routers'].values() for r in routes}
new = {(r['path'], r['method']) for routes in inv['routers'].values() for r in routes}
req(old <= new, 'v3.8 routes not preserved')
for path in [
    '/decision-module-registry', '/decision-module-registry/modules',
    '/decision-module-registry/modules/{module_id}', '/decision-module-registry/capabilities',
    '/decision-module-registry/providers', '/decision-module-registry/readiness',
    '/decision-module-registry/validate'
]:
    req(repr(path) in registry_routes, f'registry route missing {path}')

req(manifest == pmanifest, 'release manifest parity')
req(manifest['release'] == VERSION and manifest['build_fingerprint'] == BUILD and manifest['source_commit'] == SOURCE, 'manifest identity')
req(manifest['backend']['route_count'] == 249 and manifest['backend']['route_registry_count'] == 19, 'manifest backend counts')
req(manifest['backend']['included_router_count'] == 20 and manifest['backend']['previous_route_count'] == 242, 'manifest router lineage')
req(manifest['migration']['database_schema'] is False, 'v3.9 must not add schema migration')
req(manifest['migration']['unified_decision_module_registry'] is True, 'v3.9 registry migration flag')
req(manifest['unified_module_registry']['schema'] == REGISTRY_SCHEMA, 'manifest unified registry schema')
req(manifest['unified_module_registry']['canonical'] is True, 'unified registry canonical')
req(manifest['unified_module_registry']['module_count'] == 4 and manifest['unified_module_registry']['all_modules_authoritative'] is True, 'all modules authoritative')
req(manifest['unified_module_registry']['legacy_decision_modules_endpoints_preserved'] is True, 'legacy module endpoints preserved')
req(manifest['unified_module_registry']['final_decision_authority'] == 'human-governed', 'human decision authority')
req(manifest['next_release'].startswith('3.10.0'), 'next release')

req(registry_contract['schema'] == REGISTRY_SCHEMA and registry_contract['module_count'] == 4, 'registry contract identity')
req(set(registry_contract['module_ids']) == MODULE_IDS, 'registry module IDs')
req(registry_contract['registry_authority'] == 'decision-studio-kernel', 'registry authority')
req(registry_contract['compatibility']['legacy_decision_modules_endpoints_preserved'] is True, 'legacy registry compatibility')
req(registry_contract['compatibility']['public_api_breaking_change'] is False, 'no public API break')
req(registry_contract['governance']['registry_does_not_auto_recommend'] is True, 'no registry auto recommendation')
req(registry_contract['governance']['registry_does_not_auto_approve'] is True, 'no registry auto approval')
mods = {m['module_id']: m for m in registry_contract['modules']}
req(set(mods) == MODULE_IDS, 'registry modules')
for mid, module in mods.items():
    req(module['status'] == 'python-domain-authoritative', f'{mid} authority')
    req(module['authority']['storage'] == 'python-postgresql', f'{mid} storage authority')
    req(module['security']['read_scope'] and module['security']['write_scope'], f'{mid} scopes')
req(mods['finance']['authority']['compute'] == 'workbench', 'Finance Workbench compute authority')
req(mods['global-impact']['authority']['compute'] == 'workbench', 'Global Impact Workbench compute authority')
req(registry_contract['readiness']['all_modules_authoritative'] is True, 'registry authoritative readiness')

req(schema['revision'] == REVISION and schema['table_count'] == 20, 'schema manifest')
req(schema['authority'] == 'python-postgresql' and schema['live_write_authority'] is True, 'schema authority')
req(schema['unified_module_registry_schema'] == REGISTRY_SCHEMA and schema['unified_module_registry_canonical'] is True, 'schema registry annotation')
req(len(schema['tables']) == 20 and len(set(schema['tables'])) == 20, 'schema inventory')
req(contract['database_schema_migration'] is False and contract['new_schema_migration_in_v3_9'] is False, 'no v3.9 schema migration')
req(contract['unified_module_registry_schema'] == REGISTRY_SCHEMA and contract['unified_module_registry_canonical'] is True, 'persistence registry annotation')
req(contract['final_decision_authority'] == 'human-governed', 'final human authority')
for table in schema['tables']:
    req(f'__tablename__ = "{table}"' in models, f'model missing {table}')
    req(f'"{table}"' in migration, f'migration missing {table}')
req(REVISION in migration and REVISION in persistence, 'revision identity')
req(len(REVISION) <= 32, 'Alembic revision length')
req('PERSISTENCE_AUTHORITY = "python-postgresql"' in persistence, 'persistence authority')
for dep in ['SQLAlchemy==2.0.36', 'psycopg[binary]==3.2.3', 'alembic==1.14.0']:
    req(dep in requirements, f'missing dependency {dep}')

req(' * Version: 3.9.0' in php and "const VERSION = '3.9.0';" in php, 'plugin release metadata')
req("const DB_VERSION = '3.0.0';" in php, 'WordPress DB version preserved')
req(f"const UNIFIED_DECISION_MODULE_REGISTRY_SCHEMA = '{REGISTRY_SCHEMA}';" in php, 'plugin registry schema')
req('Stable tag: 3.9.0' in readme, 'plugin stable tag')
req(BUILD in php and SOURCE in php, 'plugin identity')
req('sustainable-catalyst-decision-studio:3.9.0' in compose, 'compose image version')
req(BUILD in compose and SOURCE in compose, 'compose identity')
req('SCDS_PERSISTENCE_REQUIRED: "true"' in compose and 'SCDS_PERSISTENCE_WRITE_ENABLED: "true"' in compose, 'persistence gates')
req("d.get('version') == '3.9.0'" in docker, 'Docker health version')
req(BUILD in docker and SOURCE in docker, 'Docker identity')
req(BUILD in render and SOURCE in render, 'render identity')

for path in [
    'data/backend_route_inventory_v3.8.0.json', 'data/decision_studio_release_manifest_v3.8.0.json',
    'data/global_impact_python_domain_contract_v3.8.0.json', 'data/narrative_risk_python_domain_contract_v3.7.0.json',
    'data/finance_python_domain_contract_v3.6.0.json', 'data/canvas_python_domain_contract_v3.5.0.json',
    'backend/app/domains/canvas.py', 'backend/app/domains/finance.py', 'backend/app/domains/narrative_risk.py', 'backend/app/domains/global_impact.py',
    'backend/app/persistence/repository.py', 'backend/app/decision_kernel.py'
]:
    req((ROOT / path).exists(), f'preserved {path}')
req('.venv-*/' in text('.gitignore') and '.venv/' in text('.gitignore'), 'virtualenv ignore rules')
tracked = [p for p in ROOT.rglob('*') if p.is_file() and any(part.startswith('.venv') for part in p.relative_to(ROOT).parts)]
req(not tracked, f'local virtualenv files present: {tracked[:3]}')
jsons = [p for p in ROOT.rglob('*.json') if '.git' not in p.parts]
for p in jsons:
    load(p)
print(f'Decision Studio v{VERSION} release-integrity checks passed: canonical Unified Decision Module Registry, 7 registry routes, all four Python/PostgreSQL authoritative domains, capability/provider/readiness indexes, legacy /decision-modules compatibility, 20 persistence tables on preserved Alembic revision {REVISION}, 19 route registries, 249 certified API routes, Workbench compute boundaries preserved, human-governed final decision authority, and {len(jsons)} JSON files validated.')
