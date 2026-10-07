#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v3.8.0."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'wordpress-plugin' / 'sustainable-catalyst-decision-studio'
VERSION = '3.8.0'
BUILD = 'scds-v3.8.0-global-impact-catalyst-python-domain-migration'
SOURCE = 'release-v3.8.0'
REVISION = '0001_v330_pg_foundation'
CANVAS_SCHEMA = 'scds-canvas-domain/1.0'
FINANCE_SCHEMA = 'scds-finance-domain/1.0'
NARRATIVE_SCHEMA = 'scds-narrative-risk-domain/1.0'
GLOBAL_IMPACT_SCHEMA = 'scds-global-impact-domain/1.0'


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
kernel = text('backend/app/decision_kernel.py')
canvas = text('backend/app/domains/canvas.py')
finance = text('backend/app/domains/finance.py')
narrative = text('backend/app/domains/narrative_risk.py')
global_impact = text('backend/app/domains/global_impact.py')
migration = text('backend/migrations/versions/0001_v330_pg_foundation.py')
api_router = text('backend/app/api/router.py')
global_impact_routes = text('backend/app/api/routes/global_impact.py')
requirements = text('backend/requirements.txt')
php = (PLUGIN / 'sustainable-catalyst-decision-studio.php').read_text(encoding='utf-8')
readme = (PLUGIN / 'readme.txt').read_text(encoding='utf-8')
docker = text('backend/Dockerfile')
compose = text('compose.yml')
render = text('backend/render.yaml')
inv = load(ROOT / 'data/backend_route_inventory_v3.8.0.json')
previous = load(ROOT / 'data/backend_route_inventory_v3.7.0.json')
manifest = load(ROOT / 'data/decision_studio_release_manifest_v3.8.0.json')
pmanifest = load(PLUGIN / 'data/release_manifest_v3.8.0.json')
schema = load(ROOT / 'data/postgresql_schema_manifest_v3.8.0.json')
contract = load(ROOT / 'data/postgresql_persistence_contract_v3.8.0.json')
impact_contract = load(ROOT / 'data/global_impact_python_domain_contract_v3.8.0.json')

req('from app.api.router import api_router' in main and 'app.include_router(api_router)' in main, 'composition router')
req('@app.get' not in main and '@app.post' not in main, 'main contains endpoint decorators')
req(f'APP_VERSION = "{VERSION}"' in service, 'service version')
req(BUILD in service and SOURCE in service, 'service identity')
req('GLOBAL_IMPACT_DOMAIN_SCHEMA' in service and 'GlobalImpactDomainRepository' in service, 'Global Impact service integration')
req('from app.api.routes.global_impact import router as global_impact_router' in api_router, 'Global Impact router imported')
req('api_router.include_router(global_impact_router)' in api_router, 'Global Impact router mounted')

route_dir = ROOT / 'backend/app/api/routes'
router_modules = sorted(p for p in route_dir.glob('*.py') if p.name != '__init__.py')
req(len(router_modules) == 18, f'expected 18 route registry modules, got {len(router_modules)}')
route_text = '\n'.join(p.read_text(encoding='utf-8') for p in router_modules)
for routes in inv['routers'].values():
    for route in routes:
        if route['path'].startswith('/v1/energy-runtime/'):
            continue
        req(repr(route['path']) in route_text, f"missing route {route['path']}")
req(inv['route_count'] == 242, 'v3.8 route count')
req(len(inv['routers']['global_impact']) == 11, 'Global Impact route count')
old = {(r['path'], r['method']) for routes in previous['routers'].values() for r in routes}
new = {(r['path'], r['method']) for routes in inv['routers'].values() for r in routes}
req(old <= new, 'v3.7 routes not preserved')

req(manifest == pmanifest, 'release manifest parity')
req(manifest['release'] == VERSION and manifest['build_fingerprint'] == BUILD and manifest['source_commit'] == SOURCE, 'manifest identity')
req(manifest['backend']['route_count'] == 242 and manifest['backend']['route_registry_count'] == 18, 'manifest backend counts')
req(manifest['migration']['database_schema'] is False, 'v3.8 must not add schema migration')
req(manifest['migration']['authority_cutover'] is False, 'v3.8 must not repeat repository cutover')
req(manifest['migration']['narrative_risk_python_domain_authority'] is False, 'Narrative Risk migration not repeated')
req(manifest['migration']['global_impact_python_domain_authority'] is True, 'Global Impact authority migration')
for key in ['canvas_python_domain_authoritative', 'finance_python_domain_authoritative', 'narrative_risk_python_domain_authoritative', 'global_impact_python_domain_authoritative']:
    req(manifest['decision_kernel'][key] is True, f'{key} not authoritative')
req(manifest['decision_kernel']['finance_compute_authority'] == 'workbench', 'Finance Workbench compute authority')
req(manifest['decision_kernel']['global_impact_compute_authority'] == 'workbench', 'Global Impact Workbench compute authority')
req(manifest['decision_kernel']['final_decision_authority'] == 'human-governed', 'human decision authority')
req(manifest['global_impact']['schema'] == GLOBAL_IMPACT_SCHEMA and manifest['global_impact']['status'] == 'python-domain-authoritative', 'Global Impact manifest identity')
req(manifest['next_release'].startswith('3.9.0'), 'next release')

req(schema['revision'] == REVISION and schema['table_count'] == 20, 'schema manifest')
req(schema['authority'] == 'python-postgresql' and schema['live_write_authority'] is True, 'schema authority')
req(schema['canvas_python_domain_authoritative'] is True and schema['finance_python_domain_authoritative'] is True and schema['narrative_risk_python_domain_authoritative'] is True, 'prior domains preserved')
req(schema['global_impact_domain_schema'] == GLOBAL_IMPACT_SCHEMA and schema['global_impact_python_domain_authoritative'] is True, 'Global Impact schema annotation')
req(len(schema['tables']) == 20 and len(set(schema['tables'])) == 20, 'schema inventory')
req(contract['database_schema_migration'] is False and contract['new_schema_migration_in_v3_8'] is False, 'no v3.8 schema migration')
req(contract['postgresql_live_authority'] is True and contract['python_repository_live_authority'] is True, 'repository authority')
req(contract['global_impact_domain_schema'] == GLOBAL_IMPACT_SCHEMA and contract['global_impact_python_domain_authoritative'] is True, 'Global Impact persistence contract')
req(contract['global_impact_compute_authority'] == 'workbench', 'Global Impact compute authority')
req(contract['final_decision_authority'] == 'human-governed', 'final human authority')

req(impact_contract['schema'] == GLOBAL_IMPACT_SCHEMA and impact_contract['status'] == 'python-domain-authoritative', 'Global Impact contract identity')
req(impact_contract['storage_authority'] == 'python-postgresql' and impact_contract['compute_authority'] == 'workbench', 'Global Impact authorities')
req(impact_contract['security']['read_scope'] == 'global-impact:read' and impact_contract['security']['write_scope'] == 'global-impact:write', 'Global Impact scopes')
req(impact_contract['compatibility']['legacy_global_impact_import'] is True, 'legacy Global Impact import')
b = impact_contract['boundaries']
req(b['sdg_alignment_is_not_proof_of_impact'] is True and b['modeled_impact_is_not_observed_outcome'] is True, 'impact epistemic boundaries')
req(b['indicator_change_is_not_causal_attribution'] is True, 'indicator causality boundary')
req(b['decision_studio_executes_impact_models'] is False, 'Workbench compute boundary')
req(b['automatic_impact_verification'] is False and b['automatic_sustainability_rating'] is False, 'no auto impact/rating')
req(b['automatic_recommendation'] is False and b['automatic_approval'] is False, 'no auto recommendation/approval')
req(b['final_decision_authority'] == 'human-governed', 'Global Impact human authority')
req(len(impact_contract['endpoints']) == 11, 'Global Impact endpoint contract count')
for endpoint in impact_contract['endpoints']:
    path = endpoint.split(' ', 1)[1]
    req(repr(path) in global_impact_routes, f'Global Impact contract route missing {path}')

req('GLOBAL_IMPACT_DOMAIN_SCHEMA = "scds-global-impact-domain/1.0"' in global_impact, 'Global Impact schema constant')
req('class GlobalImpactDomainRepository' in global_impact, 'Global Impact repository class')
for method in ['replace_impact_claims', 'replace_indicators', 'replace_evidence_links']:
    req(method in global_impact, f'Global Impact normalized writer missing {method}')
req('GLOBAL_IMPACT_INDICATOR_ARTIFACT_TYPE = "global-impact-indicator"' in global_impact, 'Global Impact indicator artifact type')
req('"impact_verified": False' in global_impact and '"causal_attribution_verified": False' in global_impact, 'explicit impact epistemic metadata')
req('legacy_artifact' in global_impact and 'global_impact.legacy_imported' in global_impact, 'source-preserving legacy import')
req('_global_impact_scope_error' in service and 'global-impact:read' in service and 'global-impact:write' in service, 'Global Impact scoped authorization')
req('FINANCE_DOMAIN_SCHEMA = "scds-finance-domain/1.0"' in finance and 'CANVAS_DOMAIN_SCHEMA = "scds-canvas-domain/1.0"' in canvas and 'NARRATIVE_RISK_DOMAIN_SCHEMA = "scds-narrative-risk-domain/1.0"' in narrative, 'prior domains preserved')
req('"status": "python-domain-authoritative"' in kernel and '"domain_schema": "scds-global-impact-domain/1.0"' in kernel, 'Global Impact module registry authority')
req('"compute_authority": "workbench"' in kernel, 'Workbench boundary preserved')

for table in schema['tables']:
    req(f'__tablename__ = "{table}"' in models, f'model missing {table}')
    req(f'"{table}"' in migration, f'migration missing {table}')
req(REVISION in migration and REVISION in persistence, 'revision identity')
req(len(REVISION) <= 32, 'Alembic revision length')
req('PERSISTENCE_AUTHORITY = "python-postgresql"' in persistence, 'persistence authority')
req('class PersistenceRepository' in repo, 'repository preserved')
for dep in ['SQLAlchemy==2.0.36', 'psycopg[binary]==3.2.3', 'alembic==1.14.0']:
    req(dep in requirements, f'missing dependency {dep}')

req(' * Version: 3.8.0' in php and "const VERSION = '3.8.0';" in php, 'plugin release metadata')
req("const DB_VERSION = '3.0.0';" in php, 'WordPress DB version preserved')
req('Stable tag: 3.8.0' in readme, 'plugin stable tag')
req(BUILD in php and SOURCE in php, 'plugin identity')
req('sustainable-catalyst-decision-studio:3.8.0' in compose, 'compose image version')
req('SCDS_PERSISTENCE_REQUIRED: "true"' in compose and 'SCDS_PERSISTENCE_WRITE_ENABLED: "true"' in compose, 'persistence gates')
req("d.get('version') == '3.8.0'" in docker, 'Docker health version')
req(BUILD in render and SOURCE in render, 'render identity')

for path in [
    'data/backend_route_inventory_v3.7.0.json', 'data/decision_studio_release_manifest_v3.7.0.json',
    'data/narrative_risk_python_domain_contract_v3.7.0.json', 'data/finance_python_domain_contract_v3.6.0.json',
    'data/canvas_python_domain_contract_v3.5.0.json', 'data/python_decision_repository_contract_v3.4.0.json',
    'backend/app/domains/canvas.py', 'backend/app/domains/finance.py', 'backend/app/domains/narrative_risk.py',
    'backend/app/persistence/repository.py', 'backend/app/decision_kernel.py'
]:
    req((ROOT / path).exists(), f'preserved {path}')
req('.venv-*/' in text('.gitignore') and '.venv/' in text('.gitignore'), 'virtualenv ignore rules')
tracked = [p for p in ROOT.rglob('*') if p.is_file() and any(part.startswith('.venv') for part in p.relative_to(ROOT).parts)]
req(not tracked, f'local virtualenv files present: {tracked[:3]}')
jsons = [p for p in ROOT.rglob('*.json') if '.git' not in p.parts]
for p in jsons:
    load(p)
print(f'Decision Studio v{VERSION} release-integrity checks passed: Global Impact Catalyst Python domain authority, 11 Global Impact routes, claims/evidence/indicator normalization with explicit impact boundaries, 20 persistence tables on preserved Alembic revision {REVISION}, 18 route registries, 242 certified API routes, source-preserving legacy Global Impact import, Canvas/Finance/Narrative Risk authority preserved, Workbench compute boundary preserved, human-governed final decision authority, and {len(jsons)} JSON files validated.')
