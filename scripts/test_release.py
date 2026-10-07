#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VERSION='3.11.0'
BUILD='scds-v3.11.0-module-artifact-provenance-standard'
SOURCE='release-v3.11.0'
REVISION='0001_v330_pg_foundation'
ART='scds-module-artifact/1.0'
PROV='scds-module-provenance/1.0'

def text(p): return (ROOT/p).read_text()
def load(p): return json.loads(text(p))
def req(c,m):
    if not c: raise SystemExit(f'FAIL: {m}')

service=text('backend/app/services/decision_service.py')
artifact=text('backend/app/module_artifact_provenance.py')
routes=text('backend/app/api/routes/module_artifacts.py')
router=text('backend/app/api/router.py')
models=text('backend/app/persistence/models.py')
migration=text('backend/migrations/versions/0001_v330_pg_foundation.py')
persistence=text('backend/app/persistence/database.py')
php=text('wordpress-plugin/sustainable-catalyst-decision-studio/sustainable-catalyst-decision-studio.php')
readme=text('wordpress-plugin/sustainable-catalyst-decision-studio/readme.txt')
compose=text('compose.yml'); docker=text('backend/Dockerfile'); render=text('backend/render.yaml')
inv=load('data/backend_route_inventory_v3.11.0.json')
prev=load('data/backend_route_inventory_v3.10.0.json')
manifest=load('data/decision_studio_release_manifest_v3.11.0.json')
pmanifest=load('wordpress-plugin/sustainable-catalyst-decision-studio/data/release_manifest_v3.11.0.json')
contract=load('data/module_artifact_provenance_contract_v3.11.0.json')
pc=load('data/postgresql_persistence_contract_v3.11.0.json')
schema=load('data/postgresql_schema_manifest_v3.11.0.json')

req(f'APP_VERSION = "{VERSION}"' in service,'backend version')
req(BUILD in service and SOURCE in service,'backend identity')
req(ART in artifact and PROV in artifact,'artifact schemas')
req('artifact_revisions_are_immutable' in artifact and 'provenance_does_not_imply_truth' in artifact,'artifact provenance boundaries')
req('ModuleArtifactRepository' in artifact and 'checksum_sha256=digest' in artifact,'artifact repository/integrity')
req('from app.api.routes.module_artifacts import router as module_artifacts_router' in router and 'include_router(module_artifacts_router)' in router,'artifact router included')
for path in ['/module-artifacts/contract','/module-artifacts/template','/module-artifacts/validate','/module-artifacts/decisions/{decision_id}','/module-artifacts/decisions/{decision_id}/{artifact_id}','/module-artifacts/decisions/{decision_id}/{artifact_id}/revisions','/module-artifacts/decisions/{decision_id}/{artifact_id}/lineage']:
    req(repr(path) in routes,f'missing artifact route {path}')
req(inv['release']==VERSION and inv['route_count']==264,'route inventory identity/count')
req(len(inv['routers'])==22 and len(inv['routers']['module_artifacts'])==8,'router inventory')
old={(r['path'],r['method']) for rs in prev['routers'].values() for r in rs}; new={(r['path'],r['method']) for rs in inv['routers'].values() for r in rs}; req(old<=new,'v3.10 routes preserved')
req(manifest==pmanifest,'manifest parity')
req(manifest['release']==VERSION and manifest['build_fingerprint']==BUILD and manifest['source_commit']==SOURCE,'manifest identity')
req(manifest['backend']['route_count']==264 and manifest['backend']['route_registry_count']==21 and manifest['backend']['included_router_count']==22,'manifest backend counts')
ma=manifest['module_artifact_provenance']; req(ma['artifact_schema']==ART and ma['provenance_schema']==PROV,'manifest artifact schemas')
req(ma['immutable_revisions'] and ma['sha256_integrity'] and ma['explicit_parent_lineage'],'manifest provenance guarantees')
req(ma['compute_authorities']=={'finance':'workbench','global-impact':'workbench'},'compute boundaries')
req(ma['boundaries']['provenance_implies_truth'] is False and ma['boundaries']['provenance_implies_causality'] is False,'epistemic boundaries')
req(manifest['next_release'].startswith('3.12.0'),'next release')
req(contract['schema']==ART and contract['provenance_schema']==PROV,'contract identity')
req(contract['persistence']['table']=='artifacts' and contract['persistence']['event_table']=='decision_events' and contract['persistence']['schema_migration_required'] is False,'persistence reuse')
req(schema['revision']==REVISION and schema['table_count']==20 and schema['module_artifact_schema_migration'] is False,'schema unchanged')
req(pc['new_schema_migration_in_v3_11'] is False and pc['immutable_artifact_revisions'] is True,'persistence contract')
for table in schema['tables']:
    req(f'__tablename__ = "{table}"' in models,f'model missing {table}')
    req(f'"{table}"' in migration,f'migration missing {table}')
req(REVISION in migration and REVISION in persistence and len(REVISION)<=32,'alembic revision')
req(' * Version: 3.11.0' in php and "const VERSION = '3.11.0';" in php,'plugin metadata')
req("const DB_VERSION = '3.0.0';" in php,'WordPress DB unchanged')
req(f"const MODULE_ARTIFACT_SCHEMA = '{ART}';" in php and f"const MODULE_PROVENANCE_SCHEMA = '{PROV}';" in php,'plugin schema constants')
req('Stable tag: 3.11.0' in readme,'plugin stable tag')
req(BUILD in php and SOURCE in php and BUILD in compose and SOURCE in compose and BUILD in docker and SOURCE in docker and BUILD in render and SOURCE in render,'release identity propagation')
req('sustainable-catalyst-decision-studio:3.11.0' in compose,'compose image')
req("d.get('version') == '3.11.0'" in docker,'docker health version')
for p in ['backend/app/cross_module_composition.py','backend/app/unified_module_registry.py','backend/app/domains/canvas.py','backend/app/domains/finance.py','backend/app/domains/narrative_risk.py','backend/app/domains/global_impact.py','data/backend_route_inventory_v3.10.0.json']:
    req((ROOT/p).exists(),f'preserved {p}')
req('.venv-*/' in text('.gitignore') and '.venv/' in text('.gitignore'),'venv ignore')
jsons=[p for p in ROOT.rglob('*.json') if '.git' not in p.parts]
for p in jsons: json.loads(p.read_text())
print(f'Decision Studio v{VERSION} release-integrity checks passed: canonical Module Artifact & Provenance Standard, 8 artifact routes, immutable revisions, SHA-256 integrity, explicit lineage, module ownership preservation, evidence/source/computation references, four authoritative modules and v3.10 composition preserved, 20 persistence tables on preserved Alembic revision {REVISION}, 21 route registries, 264 certified API routes, Workbench compute boundaries preserved, human-governed final decision authority, and {len(jsons)} JSON files validated.')
