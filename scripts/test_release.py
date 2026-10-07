#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v3.7.0."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'wordpress-plugin' / 'sustainable-catalyst-decision-studio'
VERSION = '3.7.0'
BUILD = 'scds-v3.7.0-narrative-risk-python-domain-migration'
SOURCE = 'release-v3.7.0'
REVISION = '0001_v330_pg_foundation'
NARRATIVE_SCHEMA = 'scds-narrative-risk-domain/1.0'
FINANCE_SCHEMA = 'scds-finance-domain/1.0'
CANVAS_SCHEMA = 'scds-canvas-domain/1.0'


def req(value, message):
    if not value:
        raise AssertionError(message)

def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def text(rel):
    return (ROOT / rel).read_text(encoding='utf-8')

main=text('backend/app/main.py')
service=text('backend/app/services/decision_service.py')
persistence=text('backend/app/persistence/database.py')
models=text('backend/app/persistence/models.py')
repo=text('backend/app/persistence/repository.py')
kernel=text('backend/app/decision_kernel.py')
narrative=text('backend/app/domains/narrative_risk.py')
canvas=text('backend/app/domains/canvas.py')
finance=text('backend/app/domains/finance.py')
migration=text('backend/migrations/versions/0001_v330_pg_foundation.py')
api_router=text('backend/app/api/router.py')
narrative_routes=text('backend/app/api/routes/narrative_risk.py')
requirements=text('backend/requirements.txt')
php=(PLUGIN/'sustainable-catalyst-decision-studio.php').read_text(encoding='utf-8')
readme=(PLUGIN/'readme.txt').read_text(encoding='utf-8')
docker=text('backend/Dockerfile')
compose=text('compose.yml')
render=text('backend/render.yaml')
inv=load(ROOT/'data/backend_route_inventory_v3.7.0.json')
previous=load(ROOT/'data/backend_route_inventory_v3.6.0.json')
manifest=load(ROOT/'data/decision_studio_release_manifest_v3.7.0.json')
pmanifest=load(PLUGIN/'data/release_manifest_v3.7.0.json')
schema=load(ROOT/'data/postgresql_schema_manifest_v3.7.0.json')
contract=load(ROOT/'data/postgresql_persistence_contract_v3.7.0.json')
narrative_contract=load(ROOT/'data/narrative_risk_python_domain_contract_v3.7.0.json')

req('from app.api.router import api_router' in main and 'app.include_router(api_router)' in main, 'composition router')
req('@app.get' not in main and '@app.post' not in main, 'main contains endpoint decorators')
req(f'APP_VERSION = "{VERSION}"' in service, 'service version')
req(BUILD in service and SOURCE in service, 'service identity')
req('NARRATIVE_RISK_DOMAIN_SCHEMA' in service and 'NarrativeRiskDomainRepository' in service, 'Narrative Risk service integration')
req('from app.api.routes.narrative_risk import router as narrative_risk_router' in api_router, 'Narrative Risk router imported')
req('api_router.include_router(narrative_risk_router)' in api_router, 'Narrative Risk router mounted')

route_dir=ROOT/'backend/app/api/routes'
router_modules=sorted(p for p in route_dir.glob('*.py') if p.name!='__init__.py')
req(len(router_modules)==17, f'expected 17 route registry modules, got {len(router_modules)}')
route_text='\n'.join(p.read_text(encoding='utf-8') for p in router_modules)
for routes in inv['routers'].values():
    for route in routes:
        if route['path'].startswith('/v1/energy-runtime/'):
            continue
        req(repr(route['path']) in route_text, f"missing route {route['path']}")
req(inv['route_count']==231, 'v3.7 route count')
req(len(inv['routers']['narrative_risk'])==11, 'Narrative Risk route count')
old={(r['path'],r['method']) for routes in previous['routers'].values() for r in routes}
new={(r['path'],r['method']) for routes in inv['routers'].values() for r in routes}
req(old <= new, 'v3.6 routes not preserved')

req(manifest==pmanifest, 'release manifest parity')
req(manifest['release']==VERSION and manifest['build_fingerprint']==BUILD and manifest['source_commit']==SOURCE, 'manifest identity')
req(manifest['backend']['route_count']==231 and manifest['backend']['route_registry_count']==17, 'manifest backend counts')
req(manifest['migration']['database_schema'] is False, 'v3.7 must not add schema migration')
req(manifest['migration']['authority_cutover'] is False, 'v3.7 must not repeat repository cutover')
req(manifest['migration']['finance_python_domain_authority'] is False, 'Finance migration not repeated')
req(manifest['migration']['narrative_risk_python_domain_authority'] is True, 'Narrative Risk authority migration')
req(manifest['decision_kernel']['canvas_python_domain_authoritative'] is True, 'Canvas preserved')
req(manifest['decision_kernel']['finance_python_domain_authoritative'] is True, 'Finance preserved')
req(manifest['decision_kernel']['finance_compute_authority']=='workbench', 'Workbench finance compute authority')
req(manifest['decision_kernel']['narrative_risk_python_domain_authoritative'] is True, 'Narrative Risk authoritative')
req(manifest['decision_kernel']['final_decision_authority']=='human-governed', 'human decision authority')
req(manifest['narrative_risk']['schema']==NARRATIVE_SCHEMA and manifest['narrative_risk']['status']=='python-domain-authoritative', 'Narrative manifest identity')
req(manifest['next_release'].startswith('3.8.0'), 'next release')

req(schema['revision']==REVISION and schema['table_count']==20, 'schema manifest')
req(schema['authority']=='python-postgresql' and schema['live_write_authority'] is True, 'schema authority')
req(schema['canvas_python_domain_authoritative'] is True and schema['finance_python_domain_authoritative'] is True, 'prior domain schema annotations')
req(schema['narrative_risk_domain_schema']==NARRATIVE_SCHEMA and schema['narrative_risk_python_domain_authoritative'] is True, 'Narrative schema annotation')
req(len(schema['tables'])==20 and len(set(schema['tables']))==20, 'schema inventory')
req(contract['database_schema_migration'] is False and contract['new_schema_migration_in_v3_7'] is False, 'no v3.7 schema migration')
req(contract['postgresql_live_authority'] is True and contract['python_repository_live_authority'] is True, 'repository authority')
req(contract['narrative_risk_domain_schema']==NARRATIVE_SCHEMA and contract['narrative_risk_python_domain_authoritative'] is True, 'Narrative persistence contract')
req(contract['final_decision_authority']=='human-governed', 'final human authority')

req(narrative_contract['schema']==NARRATIVE_SCHEMA and narrative_contract['status']=='python-domain-authoritative', 'Narrative contract identity')
req(narrative_contract['storage_authority']=='python-postgresql', 'Narrative storage authority')
req(narrative_contract['security']['read_scope']=='narrative-risk:read' and narrative_contract['security']['write_scope']=='narrative-risk:write', 'Narrative scopes')
req(narrative_contract['compatibility']['legacy_narrative_risk_import'] is True, 'legacy Narrative import')
b=narrative_contract['boundaries']
req(b['claim_is_not_fact_without_evidence'] is True and b['signal_is_not_causality'] is True, 'epistemic boundaries')
req(b['automatic_truth_verification'] is False and b['automatic_causality_inference'] is False, 'no automated truth/causality')
req(b['automatic_recommendation'] is False and b['automatic_escalation_or_action'] is False, 'no auto recommendation/action')
req(b['final_decision_authority']=='human-governed', 'Narrative human authority')
req(len(narrative_contract['endpoints'])==11, 'Narrative endpoint contract count')
for endpoint in narrative_contract['endpoints']:
    path=endpoint.split(' ',1)[1]
    req(repr(path) in narrative_routes, f'Narrative contract route missing {path}')

req('NARRATIVE_RISK_DOMAIN_SCHEMA = "scds-narrative-risk-domain/1.0"' in narrative, 'Narrative schema constant')
req('class NarrativeRiskDomainRepository' in narrative, 'Narrative repository class')
for method in ['replace_claims','replace_signals','replace_evidence_links']:
    req(method in narrative, f'Narrative normalized writer missing {method}')
req('NARRATIVE_RISK_SIGNAL_ARTIFACT_TYPE = "narrative-risk-signal"' in narrative, 'Narrative signal artifact type')
req('"truth_verified": False' in narrative and '"causality_inferred": False' in narrative, 'explicit epistemic metadata')
req('legacy_artifact' in narrative and 'narrative_risk.legacy_imported' in narrative, 'source-preserving legacy import')
req('_narrative_risk_scope_error' in service and 'narrative-risk:read' in service and 'narrative-risk:write' in service, 'Narrative scoped authorization')
req('FINANCE_DOMAIN_SCHEMA = "scds-finance-domain/1.0"' in finance and 'CANVAS_DOMAIN_SCHEMA = "scds-canvas-domain/1.0"' in canvas, 'prior domains preserved')
req('"status": "python-domain-authoritative"' in kernel and '"domain_schema": "scds-narrative-risk-domain/1.0"' in kernel, 'Narrative module registry authority')
req('"compute_authority": "workbench"' in kernel, 'Finance Workbench boundary preserved')

for table in schema['tables']:
    req(f'__tablename__ = "{table}"' in models, f'model missing {table}')
    req(f'"{table}"' in migration, f'migration missing {table}')
req(REVISION in migration and REVISION in persistence, 'revision identity')
req(len(REVISION)<=32, 'Alembic revision length')
req('PERSISTENCE_AUTHORITY = "python-postgresql"' in persistence, 'persistence authority')
req('class PersistenceRepository' in repo, 'repository preserved')
for dep in ['SQLAlchemy==2.0.36','psycopg[binary]==3.2.3','alembic==1.14.0']:
    req(dep in requirements, f'missing dependency {dep}')

req(' * Version: 3.7.0' in php and "const VERSION = '3.7.0';" in php, 'plugin release metadata')
req("const DB_VERSION = '3.0.0';" in php, 'WordPress DB version preserved')
req('Stable tag: 3.7.0' in readme, 'plugin stable tag')
req(BUILD in php and SOURCE in php, 'plugin identity')
req('sustainable-catalyst-decision-studio:3.7.0' in compose, 'compose image version')
req('SCDS_PERSISTENCE_REQUIRED: "true"' in compose and 'SCDS_PERSISTENCE_WRITE_ENABLED: "true"' in compose, 'persistence gates')
req("d.get('version') == '3.7.0'" in docker, 'Docker health version')
req(BUILD in render and SOURCE in render, 'render identity')

for path in [
 'data/backend_route_inventory_v3.6.0.json','data/decision_studio_release_manifest_v3.6.0.json',
 'data/finance_python_domain_contract_v3.6.0.json','data/canvas_python_domain_contract_v3.5.0.json',
 'data/python_decision_repository_contract_v3.4.0.json','backend/app/domains/canvas.py','backend/app/domains/finance.py',
 'backend/app/persistence/repository.py','backend/app/decision_kernel.py']:
    req((ROOT/path).exists(), f'preserved {path}')
req('.venv-*/' in text('.gitignore') and '.venv/' in text('.gitignore'), 'virtualenv ignore rules')
tracked=[p for p in ROOT.rglob('*') if p.is_file() and any(part.startswith('.venv') for part in p.relative_to(ROOT).parts)]
req(not tracked, f'local virtualenv files present: {tracked[:3]}')
jsons=[p for p in ROOT.rglob('*.json') if '.git' not in p.parts]
for p in jsons: load(p)
print(f'Decision Studio v{VERSION} release-integrity checks passed: Narrative Risk Python domain authority, 11 Narrative Risk routes, evidence/claim/signal normalization with explicit epistemic boundaries, 20 persistence tables on preserved Alembic revision {REVISION}, 17 route registries, 231 certified API routes, source-preserving legacy Narrative Risk import, Canvas/Finance authority preserved, human-governed final decision authority, and {len(jsons)} JSON files validated.')
