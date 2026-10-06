#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v3.3.0."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PLUGIN=ROOT/'wordpress-plugin'/'sustainable-catalyst-decision-studio'
VERSION='3.3.0'
BUILD='scds-v3.3.0-postgresql-persistence-foundation'
SOURCE='release-v3.3.0'
REVISION='0001_v330_postgresql_persistence_foundation'


def req(value, message):
    if not value: raise AssertionError(message)
def load(path):
    with open(path,encoding='utf-8') as f: return json.load(f)
def text(rel): return (ROOT/rel).read_text(encoding='utf-8')

main=text('backend/app/main.py')
service=text('backend/app/services/decision_service.py')
persistence=text('backend/app/persistence/database.py')
models=text('backend/app/persistence/models.py')
repo=text('backend/app/persistence/repository.py')
migration=text('backend/migrations/versions/0001_v330_postgresql_persistence_foundation.py')
api_router=text('backend/app/api/router.py')
requirements=text('backend/requirements.txt')
php=(PLUGIN/'sustainable-catalyst-decision-studio.php').read_text(encoding='utf-8')
readme=(PLUGIN/'readme.txt').read_text(encoding='utf-8')
docker=text('backend/Dockerfile'); compose=text('compose.yml'); render=text('backend/render.yaml')
inv=load(ROOT/'data/backend_route_inventory_v3.3.0.json')
previous=load(ROOT/'data/backend_route_inventory_v3.2.0.json')
manifest=load(ROOT/'data/decision_studio_release_manifest_v3.3.0.json')
pmanifest=load(PLUGIN/'data/release_manifest_v3.3.0.json')
schema=load(ROOT/'data/postgresql_schema_manifest_v3.3.0.json')
contract=load(ROOT/'data/postgresql_persistence_contract_v3.3.0.json')

req('include_router(api_router)' in main,'main composition router')
req('@app.get' not in main and '@app.post' not in main,'main contains endpoint decorators')
req(len(main.splitlines()) <= 25,'main is not composition-only')
req(f'APP_VERSION = "{VERSION}"' in service,'service version')
req(BUILD in service and SOURCE in service,'service identity')
req('database_status' in service and 'persistence_status_endpoint' in service,'persistence service integration')
req('from app.api.routes.persistence import router as persistence_router' in api_router,'persistence router imported')
req('api_router.include_router(persistence_router)' in api_router,'persistence router mounted')

route_dir=ROOT/'backend/app/api/routes'
router_modules=sorted(p for p in route_dir.glob('*.py') if p.name!='__init__.py')
req(len(router_modules)==13,'expected 13 route registry modules')
route_text='\n'.join(p.read_text(encoding='utf-8') for p in router_modules)
for routes in inv['routers'].values():
    for route in routes:
        if route['path'].startswith('/v1/energy-runtime/'): continue
        req(repr(route['path']) in route_text,f"missing route {route['path']}")
req(inv['route_count']==185,'v3.3 route count')
req(len(inv['routers']['persistence'])==3,'persistence routes')
old={(r['path'],r['method']) for routes in previous['routers'].values() for r in routes}
new={(r['path'],r['method']) for routes in inv['routers'].values() for r in routes}
req(old <= new,'v3.2 routes not preserved')

req(manifest==pmanifest,'release manifest parity')
req(manifest['release']==VERSION and manifest['build_fingerprint']==BUILD and manifest['source_commit']==SOURCE,'manifest identity')
req(manifest['migration']['database'] is True,'database migration must be declared')
req(manifest['migration']['wordpress_authority'] is False,'WordPress authority must remain unchanged')
req(manifest['migration']['python_repository_authority'] is False,'Python repository authority must remain unchanged')
req(manifest['backend']['route_count']==185 and manifest['backend']['route_registry_count']==13,'manifest backend counts')
req(manifest['persistence']['authority']=='non-authoritative-foundation','persistence authority boundary')
req(manifest['persistence']['expected_schema_revision']==REVISION,'manifest schema revision')
req(manifest['persistence']['table_count']==20,'manifest table count')

req(schema['revision']==REVISION and schema['table_count']==20,'schema manifest')
req(len(schema['tables'])==20 and len(set(schema['tables']))==20,'schema table inventory')
req(contract['database_migration'] is True,'persistence contract migration')
req(contract['postgresql_live_authority'] is False,'PostgreSQL must not be live authority in v3.3')
req(contract['python_repository_authority_changed'] is False,'Python authority must not move in v3.3')
req(contract['wordpress_authority_changed'] is False,'WordPress authority must not move in v3.3')
req(contract['v3_4_authority_cutover_required'] is True,'v3.4 cutover boundary')

for table in schema['tables']:
    req(f'__tablename__ = "{table}"' in models, f'model missing {table}')
    req(f'"{table}"' in migration, f'migration missing {table}')
req(REVISION in migration and REVISION in persistence,'revision identity')
req('non-authoritative-foundation' in persistence and 'v3_4_authority_cutover_required' in persistence,'authority contract')
req('class PersistenceRepository' in repo and 'live_write_authority' in repo,'repository seam')
for dep in ['SQLAlchemy==2.0.36','psycopg[binary]==3.2.3','alembic==1.14.0']:
    req(dep in requirements,f'missing dependency {dep}')

req(' * Version: 3.3.0' in php and "const VERSION = '3.3.0';" in php,'plugin release metadata')
req("const DB_VERSION = '3.0.0';" in php,'WordPress DB version must remain 3.0.0')
req('Stable tag: 3.3.0' in readme,'plugin stable tag')
for runtime in [docker,compose,render]: req(BUILD in runtime and SOURCE in runtime,'runtime identity parity')
req('sustainable-catalyst-decision-studio:3.3.0' in compose,'compose image version')
req('postgres:16-alpine' in compose and 'decision-studio-postgres-data' in compose,'PostgreSQL compose foundation')
req('SCDS_PERSISTENCE_REQUIRED: "true"' in compose,'production DB readiness gate')
req('SCDS_PERSISTENCE_WRITE_ENABLED: "false"' in compose,'writes must remain disabled')
req("d.get('version') == '3.3.0'" in docker,'Docker health version')
req('COPY migrations ./migrations' in docker and 'COPY alembic.ini ./alembic.ini' in docker,'migration payload in image')

# v3.2 Decision Kernel contracts remain first-class.
for path in [
    'data/backend_route_inventory_v3.2.0.json','data/decision_module_registry_v3.2.0.json',
    'backend/app/decision_kernel.py','backend/tests/test_v320_decision_kernel.py',
    'backend/app/connected_decision_intelligence.py','backend/app/recommendation_review.py']:
    req((ROOT/path).exists(),f'preserved {path}')

# Local environments must not be tracked or packaged again.
req('.venv-*/' in text('.gitignore') and '.venv/' in text('.gitignore'),'virtualenv ignore rules')
tracked_venv=[p for p in ROOT.rglob('*') if p.is_file() and any(part.startswith('.venv') for part in p.relative_to(ROOT).parts)]
req(not tracked_venv, f'local virtualenv files present: {tracked_venv[:3]}')

jsons=[p for p in ROOT.rglob('*.json') if '.git' not in p.parts]
for p in jsons: load(p)
print(f'Decision Studio v{VERSION} release-integrity checks passed: PostgreSQL persistence foundation, Alembic revision {REVISION}, 20 persistence tables, 13 route registries, 185 certified API routes, non-authoritative database boundary, and {len(jsons)} JSON files validated.')
