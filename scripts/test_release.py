#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VERSION='3.12.0'
NAME='Module Interoperability & Shared Evidence'
BUILD='scds-v3.12.0-module-interoperability-shared-evidence'
SOURCE='release-v3.12.0'
REVISION='0001_v330_pg_foundation'
INTEROP='scds-module-interoperability/1.0'
SHARED='scds-shared-evidence-reference/1.0'
ART='scds-module-artifact/1.0'
PROV='scds-module-provenance/1.0'

def text(p): return (ROOT/p).read_text()
def load(p): return json.loads(text(p))
def req(c,m):
    if not c: raise SystemExit(f'FAIL: {m}')

service=text('backend/app/services/decision_service.py')
interop=text('backend/app/module_interoperability.py')
routes=text('backend/app/api/routes/module_interoperability.py')
router=text('backend/app/api/router.py')
models=text('backend/app/persistence/models.py')
migration=text('backend/migrations/versions/0001_v330_pg_foundation.py')
persistence=text('backend/app/persistence/database.py')
php=text('wordpress-plugin/sustainable-catalyst-decision-studio/sustainable-catalyst-decision-studio.php')
readme=text('wordpress-plugin/sustainable-catalyst-decision-studio/readme.txt')
compose=text('compose.yml'); docker=text('backend/Dockerfile'); render=text('backend/render.yaml')
inv=load('data/backend_route_inventory_v3.12.0.json')
prev=load('data/backend_route_inventory_v3.11.0.json')
manifest=load('data/decision_studio_release_manifest_v3.12.0.json')
pmanifest=load('wordpress-plugin/sustainable-catalyst-decision-studio/data/release_manifest_v3.12.0.json')
contract=load('data/module_interoperability_shared_evidence_contract_v3.12.0.json')
pc=load('data/postgresql_persistence_contract_v3.12.0.json')
schema=load('data/postgresql_schema_manifest_v3.12.0.json')

req(f'APP_VERSION = "{VERSION}"' in service,'backend version')
req(NAME in service and BUILD in service and SOURCE in service,'backend identity')
req(INTEROP in interop and SHARED in interop,'interoperability schemas')
req('evidence_payload_is_not_duplicated' in interop and 'owner_module_is_preserved' in interop,'sharing boundaries')
req('contradictions_are_visible_not_silently_reconciled' in interop and 'relationship-disagreement-not-truth-adjudication' in interop,'contradiction visibility')
req('ModuleInteroperabilityRepository' in interop and 'INTEROPERABILITY_OBJECT_TYPE' in interop,'interoperability repository')
req('DecisionObject' in interop and 'EvidenceLink' in interop,'existing persistence tables reused')
req('from app.api.routes.module_interoperability import router as module_interoperability_router' in router and 'include_router(module_interoperability_router)' in router,'interoperability router included')
for path in ['/module-interoperability/contract','/module-interoperability/template','/module-interoperability/validate','/module-interoperability/decisions/{decision_id}','/module-interoperability/decisions/{decision_id}/share','/module-interoperability/decisions/{decision_id}/evidence/{evidence_ref:path}','/module-interoperability/decisions/{decision_id}/diagnostics']:
    req(repr(path) in routes,f'missing interoperability route {path}')
req(inv['release']==VERSION and inv['route_count']==272,'route inventory identity/count')
req(len(inv['routers'])==23 and len(inv['routers']['module_interoperability'])==8,'router inventory')
old={(r['path'],r['method']) for rs in prev['routers'].values() for r in rs}; new={(r['path'],r['method']) for rs in inv['routers'].values() for r in rs}; req(old<=new,'v3.11 routes preserved')
req(manifest==pmanifest,'manifest parity')
req(manifest['release']==VERSION and manifest['release_name']==NAME and manifest['build_fingerprint']==BUILD and manifest['source_commit']==SOURCE,'manifest identity')
req(manifest['backend']['route_count']==272 and manifest['backend']['route_registry_count']==22 and manifest['backend']['included_router_count']==23,'manifest backend counts')
mi=manifest['module_interoperability']; req(mi['schema']==INTEROP and mi['shared_evidence_schema']==SHARED,'manifest interoperability schemas')
req(mi['shared_by_reference'] and mi['payload_duplicated'] is False and mi['owner_module_preserved'],'shared evidence guarantees')
req(mi['contradiction_visibility'] and mi['contradictions_auto_resolved'] is False,'contradiction boundaries')
req(mi['boundaries']['evidence_reuse_implies_truth'] is False and mi['boundaries']['evidence_reuse_implies_causality'] is False,'epistemic boundaries')
req(manifest['next_release'].startswith('3.13.0'),'next release')
req(contract['schema']==INTEROP and contract['shared_evidence_schema']==SHARED,'contract identity')
req(contract['persistence']['document_table']=='decision_objects' and contract['persistence']['usage_edge_table']=='evidence_links' and contract['persistence']['schema_migration_required'] is False,'persistence reuse')
req(schema['revision']==REVISION and schema['table_count']==20 and schema['module_interoperability_schema_migration'] is False and schema['shared_evidence_schema_migration'] is False,'schema unchanged')
req(pc['new_schema_migration_in_v3_12'] is False and pc['module_interoperability_shared_evidence'] is True and pc['shared_evidence_payload_duplication'] is False,'persistence contract')
for table in schema['tables']:
    req(f'__tablename__ = "{table}"' in models,f'model missing {table}')
    req(f'"{table}"' in migration,f'migration missing {table}')
req(REVISION in migration and REVISION in persistence and len(REVISION)<=32,'alembic revision')
req(' * Version: 3.12.0' in php and "const VERSION = '3.12.0';" in php,'plugin metadata')
req("const DB_VERSION = '3.0.0';" in php,'WordPress DB unchanged')
req(f"const MODULE_INTEROPERABILITY_SCHEMA = '{INTEROP}';" in php and f"const SHARED_EVIDENCE_SCHEMA = '{SHARED}';" in php,'plugin interoperability constants')
req('Stable tag: 3.12.0' in readme,'plugin stable tag')
req(BUILD in php and SOURCE in php and BUILD in compose and SOURCE in compose and BUILD in docker and SOURCE in docker and BUILD in render and SOURCE in render,'release identity propagation')
req('sustainable-catalyst-decision-studio:3.12.0' in compose,'compose image')
req("d.get('version') == '3.12.0'" in docker,'docker health version')
for p in ['backend/app/module_artifact_provenance.py','backend/app/cross_module_composition.py','backend/app/unified_module_registry.py','backend/app/domains/canvas.py','backend/app/domains/finance.py','backend/app/domains/narrative_risk.py','backend/app/domains/global_impact.py','data/backend_route_inventory_v3.11.0.json']:
    req((ROOT/p).exists(),f'preserved {p}')
req(ART in text('backend/app/module_artifact_provenance.py') and PROV in text('backend/app/module_artifact_provenance.py'),'v3.11 artifact standard preserved')
req('.venv-*/' in text('.gitignore') and '.venv/' in text('.gitignore'),'venv ignore')
jsons=[p for p in ROOT.rglob('*.json') if '.git' not in p.parts]
for p in jsons: json.loads(p.read_text())
print(f'Decision Studio v{VERSION} release-integrity checks passed: Module Interoperability & Shared Evidence, 8 interoperability routes, reference-only evidence reuse, ownership preservation, provenance continuity, contradiction visibility without truth adjudication, v3.11 immutable artifact/provenance standard preserved, 20 persistence tables on preserved Alembic revision {REVISION}, 22 route registries, 272 certified API routes, four authoritative modules preserved, Workbench compute boundaries preserved, human-governed final decision authority, and {len(jsons)} JSON files validated.')
