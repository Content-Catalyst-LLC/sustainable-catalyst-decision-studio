#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = '3.10.0'
BUILD = 'scds-v3.10.0-cross-module-decision-composition'
SOURCE = 'release-v3.10.0'
REVISION = '0001_v330_pg_foundation'
COMPOSITION_SCHEMA = 'scds-cross-module-decision-composition/1.0'
REGISTRY_SCHEMA = 'scds-unified-decision-module-registry/1.0'
MODULE_IDS = {'canvas','finance','narrative-risk','global-impact'}


def text(path: str) -> str:
    return (ROOT / path).read_text()


def load(path: str):
    return json.loads(text(path))


def req(condition, message: str):
    if not condition:
        raise SystemExit(f'FAIL: {message}')

service = text('backend/app/services/decision_service.py')
composition = text('backend/app/cross_module_composition.py')
composition_routes = text('backend/app/api/routes/composition.py')
router = text('backend/app/api/router.py')
models = text('backend/app/persistence/models.py')
persistence = text('backend/app/persistence/database.py')
migration = text('backend/migrations/versions/0001_v330_pg_foundation.py')
requirements = text('backend/requirements.txt')
php = text('wordpress-plugin/sustainable-catalyst-decision-studio/sustainable-catalyst-decision-studio.php')
readme = text('wordpress-plugin/sustainable-catalyst-decision-studio/readme.txt')
compose = text('compose.yml')
docker = text('backend/Dockerfile')
render = text('backend/render.yaml')

inv = load('data/backend_route_inventory_v3.10.0.json')
previous = load('data/backend_route_inventory_v3.9.0.json')
manifest = load('data/decision_studio_release_manifest_v3.10.0.json')
pmanifest = load('wordpress-plugin/sustainable-catalyst-decision-studio/data/release_manifest_v3.10.0.json')
contract = load('data/postgresql_persistence_contract_v3.10.0.json')
schema = load('data/postgresql_schema_manifest_v3.10.0.json')
composition_contract = load('data/cross_module_decision_composition_contract_v3.10.0.json')
composition_sample = load('data/cross_module_decision_composition_sample_v3.10.0.json')

req(f'APP_VERSION = "{VERSION}"' in service, 'backend version')
req(BUILD in service and SOURCE in service, 'backend release identity')
req(COMPOSITION_SCHEMA in composition and 'CROSS_MODULE_COMPOSITION_OBJECT_TYPE = "cross-module-decision-composition"' in composition, 'composition contract code')
req('composition_does_not_infer_causality' in composition and 'composition_does_not_auto_recommend' in composition, 'composition governance boundaries')
req('CrossModuleCompositionRepository' in composition, 'composition repository')
req('from app.api.routes.composition import router as composition_router' in router and 'include_router(composition_router)' in router, 'composition router included')
for path in [
    '/decision-composition/contract', '/decision-composition/template', '/decision-composition/validate',
    '/decision-composition/decisions/{decision_id}', '/decision-composition/decisions/{decision_id}/refresh',
    '/decision-composition/decisions/{decision_id}/diagnostics'
]:
    req(repr(path) in composition_routes, f'composition route missing {path}')

req(inv['release'] == VERSION and inv['release_name'] == 'Cross-Module Decision Composition', 'route inventory identity')
req(inv['route_count'] == 256, 'route inventory count')
req(len(inv['routers']) == 21, 'route inventory router buckets')
req(len(inv['routers']['composition']) == 7, 'composition route count')
old = {(r['path'], r['method']) for routes in previous['routers'].values() for r in routes}
new = {(r['path'], r['method']) for routes in inv['routers'].values() for r in routes}
req(old <= new, 'v3.9 routes not preserved')

req(manifest == pmanifest, 'release manifest parity')
req(manifest['release'] == VERSION and manifest['build_fingerprint'] == BUILD and manifest['source_commit'] == SOURCE, 'manifest identity')
req(manifest['backend']['route_count'] == 256 and manifest['backend']['route_registry_count'] == 20, 'manifest backend counts')
req(manifest['backend']['included_router_count'] == 21 and manifest['backend']['previous_route_count'] == 249, 'manifest router lineage')
req(manifest['migration']['database_schema'] is False, 'v3.10 must not add schema migration')
req(manifest['migration']['cross_module_decision_composition'] is True, 'composition migration flag')
cm = manifest['cross_module_composition']
req(cm['schema'] == COMPOSITION_SCHEMA and cm['minimum_modules'] == 2, 'manifest composition schema')
req(cm['explicit_cross_module_links'] is True and cm['module_ownership_preserved'] is True, 'composition ownership/link rules')
req(cm['boundaries']['composition_infers_truth'] is False and cm['boundaries']['composition_infers_causality'] is False, 'composition epistemic boundaries')
req(cm['boundaries']['composition_auto_recommends'] is False and cm['boundaries']['composition_auto_approves'] is False, 'composition governance')
req(cm['boundaries']['final_decision_authority'] == 'human-governed', 'human decision authority')
req(manifest['next_release'].startswith('3.11.0'), 'next release')

req(composition_contract['schema'] == COMPOSITION_SCHEMA and composition_contract['minimum_modules'] == 2, 'composition contract identity')
req(set(composition_contract['canonical_modules']) == MODULE_IDS, 'composition canonical modules')
req(composition_contract['principles']['module_objects_retain_domain_ownership'] is True, 'domain ownership preserved')
req(composition_contract['principles']['composition_links_are_explicit_not_inferred'] is True, 'explicit links')
req(composition_contract['compute_authorities'] == {'finance':'workbench','global-impact':'workbench'}, 'compute authorities')
req(composition_contract['security']['read_scope'] == 'composition:read' and composition_contract['security']['write_scope'] == 'composition:write', 'composition scopes')
req(composition_sample['schema'] == COMPOSITION_SCHEMA and len(composition_sample['selected_modules']) == 4, 'composition sample')

req(schema['revision'] == REVISION and schema['table_count'] == 20, 'schema manifest')
req(schema['authority'] == 'python-postgresql' and schema['live_write_authority'] is True, 'schema authority')
req(schema['cross_module_composition_schema'] == COMPOSITION_SCHEMA and schema['cross_module_composition_schema_migration'] is False, 'schema composition annotation')
req(len(schema['tables']) == 20 and len(set(schema['tables'])) == 20, 'schema inventory')
req(contract['database_schema_migration'] is False and contract['new_schema_migration_in_v3_10'] is False, 'no v3.10 schema migration')
req(contract['cross_module_composition_schema'] == COMPOSITION_SCHEMA and contract['cross_module_composition_table'] == 'decision_objects', 'persistence composition annotation')
req(contract['final_decision_authority'] == 'human-governed', 'final human authority')
for table in schema['tables']:
    req(f'__tablename__ = "{table}"' in models, f'model missing {table}')
    req(f'"{table}"' in migration, f'migration missing {table}')
req(REVISION in migration and REVISION in persistence, 'revision identity')
req(len(REVISION) <= 32, 'Alembic revision length')
req('PERSISTENCE_AUTHORITY = "python-postgresql"' in persistence, 'persistence authority')
for dep in ['SQLAlchemy==2.0.36', 'psycopg[binary]==3.2.3', 'alembic==1.14.0']:
    req(dep in requirements, f'missing dependency {dep}')

req(' * Version: 3.10.0' in php and "const VERSION = '3.10.0';" in php, 'plugin release metadata')
req("const DB_VERSION = '3.0.0';" in php, 'WordPress DB version preserved')
req(f"const CROSS_MODULE_COMPOSITION_SCHEMA = '{COMPOSITION_SCHEMA}';" in php, 'plugin composition schema')
req('Stable tag: 3.10.0' in readme, 'plugin stable tag')
req(BUILD in php and SOURCE in php, 'plugin identity')
req('sustainable-catalyst-decision-studio:3.10.0' in compose, 'compose image version')
req(BUILD in compose and SOURCE in compose, 'compose identity')
req('SCDS_PERSISTENCE_REQUIRED: "true"' in compose and 'SCDS_PERSISTENCE_WRITE_ENABLED: "true"' in compose, 'persistence gates')
req("d.get('version') == '3.10.0'" in docker, 'Docker health version')
req(BUILD in docker and SOURCE in docker, 'Docker identity')
req(BUILD in render and SOURCE in render, 'render identity')

for path in [
    'data/backend_route_inventory_v3.9.0.json', 'data/decision_studio_release_manifest_v3.9.0.json',
    'data/unified_decision_module_registry_contract_v3.9.0.json',
    'data/global_impact_python_domain_contract_v3.8.0.json', 'data/narrative_risk_python_domain_contract_v3.7.0.json',
    'data/finance_python_domain_contract_v3.6.0.json', 'data/canvas_python_domain_contract_v3.5.0.json',
    'backend/app/unified_module_registry.py', 'backend/app/domains/canvas.py', 'backend/app/domains/finance.py',
    'backend/app/domains/narrative_risk.py', 'backend/app/domains/global_impact.py',
    'backend/app/persistence/repository.py', 'backend/app/decision_kernel.py'
]:
    req((ROOT / path).exists(), f'preserved {path}')
req('.venv-*/' in text('.gitignore') and '.venv/' in text('.gitignore'), 'virtualenv ignore rules')
tracked = [p for p in ROOT.rglob('*') if p.is_file() and any(part.startswith('.venv') for part in p.relative_to(ROOT).parts)]
req(not tracked, f'local virtualenv files present: {tracked[:3]}')
jsons = [p for p in ROOT.rglob('*.json') if '.git' not in p.parts]
for p in jsons:
    json.loads(p.read_text())
print(f'Decision Studio v{VERSION} release-integrity checks passed: governed Cross-Module Decision Composition, 7 composition routes, explicit cross-module links, module ownership preservation, module-fingerprint staleness diagnostics, all four Python/PostgreSQL authoritative domains, canonical Unified Decision Module Registry preserved, 20 persistence tables on preserved Alembic revision {REVISION}, 20 route registries, 256 certified API routes, Workbench compute boundaries preserved, human-governed final decision authority, and {len(jsons)} JSON files validated.')
