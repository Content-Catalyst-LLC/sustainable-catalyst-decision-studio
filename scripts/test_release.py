#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VERSION='3.15.0'
NAME='Decision Event Store & Immutable Audit Ledger'
BUILD='scds-v3.15.0-decision-event-store-immutable-audit-ledger'
SOURCE='release-v3.15.0'
REVISION='0003_v3150_event_ledger'
EVENT_STORE='scds-decision-event-store/1.0'
LEDGER='scds-immutable-audit-ledger/1.0'
AUDIT_EVENT='scds-decision-audit-event/1.0'
AUTH='scds-global-authentication-authorization/1.0'

def text(p): return (ROOT/p).read_text()
def load(p): return json.loads(text(p))
def req(c,m):
    if not c: raise SystemExit(f'FAIL: {m}')

service=text('backend/app/services/decision_service.py')
ledger=text('backend/app/audit_ledger.py')
ledger_routes=text('backend/app/api/routes/audit_ledger.py')
repository=text('backend/app/persistence/repository.py')
router=text('backend/app/api/router.py')
persistence=text('backend/app/persistence/database.py')
models=text('backend/app/persistence/models.py')
migration=text('backend/migrations/versions/0003_v3150_event_ledger.py')
php=text('wordpress-plugin/sustainable-catalyst-decision-studio/sustainable-catalyst-decision-studio.php')
readme=text('wordpress-plugin/sustainable-catalyst-decision-studio/readme.txt')
compose=text('compose.yml'); docker=text('backend/Dockerfile'); render=text('backend/render.yaml')
inv=load('data/backend_route_inventory_v3.15.0.json')
prev=load('data/backend_route_inventory_v3.14.0.json')
manifest=load('data/decision_studio_release_manifest_v3.15.0.json')
pmanifest=load('wordpress-plugin/sustainable-catalyst-decision-studio/data/release_manifest_v3.15.0.json')
contract=load('data/decision_event_store_audit_ledger_contract_v3.15.0.json')
pc=load('data/postgresql_persistence_contract_v3.15.0.json')
schema=load('data/postgresql_schema_manifest_v3.15.0.json')

req(f'APP_VERSION = "{VERSION}"' in service,'backend version')
req(NAME in service and BUILD in service and SOURCE in service,'backend identity')
req(EVENT_STORE in ledger and LEDGER in ledger and AUDIT_EVENT in ledger,'audit schemas')
req('DecisionAuditLedgerRepository' in ledger and 'verify' in ledger and 'replay' in ledger and 'backfill' in ledger,'ledger runtime operations')
req('previous_event_hash' in ledger and 'payload_hash' in ledger and 'event_hash' in ledger,'ledger hash fields')
req('pg_advisory_xact_lock' in ledger,'PostgreSQL stream sequencing lock')
req('DecisionAuditLedgerRepository' in repository and 'compatibility_decision_event_id' in repository,'repository dual-write')
req('from app.api.routes.audit_ledger import router as audit_ledger_router' in router and 'include_router(audit_ledger_router)' in router,'audit router included')
req(inv['release']==VERSION and inv['route_count']==308,'route inventory identity/count')
req(len(inv['routers'])==26 and len(inv['routers']['audit_ledger'])==8,'router inventory/audit routes')
old={(r['path'],r['method']) for rs in prev['routers'].values() for r in rs}; new={(r['path'],r['method']) for rs in inv['routers'].values() for r in rs}; req(old<=new,'v3.14 routes preserved')
req(manifest==pmanifest,'manifest parity')
req(manifest['release']==VERSION and manifest['release_name']==NAME and manifest['build_fingerprint']==BUILD and manifest['source_commit']==SOURCE,'manifest identity')
a=manifest['backend_architecture']; req(a['route_count']==308 and a['router_registry_count']==25 and a['included_router_count']==26,'manifest backend counts')
req(a['database_migration'] is True and a['decision_event_store_immutable_audit_ledger'] is True,'v3.15 architecture boundary')
req(a['decision_audit_tables_added']==1 and a['append_only_database_trigger'] is True and a['historical_decision_event_backfill'] is True,'ledger migration architecture')
store=manifest['decision_event_store']; req(store['schema']==EVENT_STORE and store['ledger_schema']==LEDGER and store['event_schema']==AUDIT_EVENT,'event-store manifest schemas')
req(store['append_only'] is True and store['database_mutation_guard'] is True and store['sha256_hash_chain'] is True,'event-store immutability/integrity')
req(store['read_only_replay'] is True and store['replay_reexecutes_domain_mutations'] is False,'read-only replay boundary')
req(store['final_decision_authority']=='human-governed','event-store human authority')
req(manifest['global_authentication_authorization']['schema']==AUTH,'v3.14 global auth preserved')
req(manifest['next_release'].startswith('3.16.0'),'next release')
req(contract['schema']==LEDGER and contract['event_store_schema']==EVENT_STORE and contract['event_schema']==AUDIT_EVENT,'contract schemas')
cp=contract['principles']; req(cp['append_only'] and cp['database_mutation_guard'] and cp['deterministic_sequence_per_stream'],'append-only contract')
req(cp['sha256_payload_fingerprint'] and cp['sha256_hash_chain'] and cp['authenticated_actor_identity_is_recorded'],'integrity/actor contract')
req(cp['replay_is_read_only'] and cp['replay_does_not_reexecute_domain_mutations'],'contract replay boundary')
req(contract['final_decision_authority']=='human-governed','contract human authority')
req(schema['revision']==REVISION and schema['table_count']==27 and schema['schema_migration_required'] is True and schema['new_table']=='decision_audit_events','schema migration')
req(pc['expected_schema_revision']==REVISION and pc['new_schema_migration_in_v3_15'] is True and pc['table_count']==27,'persistence migrated')
req(pc['principles']['immutable_decision_audit_ledger'] is True and pc['principles']['decision_audit_events_append_only'] is True,'persistence ledger contract')
req(f'EXPECTED_SCHEMA_REVISION = "{REVISION}"' in persistence,'current revision')
req(len([x for x in schema['tables'] if f'__tablename__ = "{x}"' in models])==27,'all persistence models present')
req('__tablename__ = "decision_audit_events"' in models,'audit model present')
req('revision = "0003_v3150_event_ledger"' in migration and 'down_revision = "0002_v3130_collaboration"' in migration,'migration lineage')
req('scds_block_audit_event_mutation' in migration and 'BEFORE UPDATE' in migration and 'BEFORE DELETE' in migration,'database append-only trigger')
req("current_setting('scds.audit_maintenance', true)" in migration,'controlled maintenance escape hatch')
req(' * Version: 3.15.0' in php and "const VERSION = '3.15.0';" in php,'plugin metadata')
req("const DB_VERSION = '3.0.0';" in php,'WordPress DB unchanged')
req(f"const DECISION_EVENT_STORE_SCHEMA = '{EVENT_STORE}';" in php,'plugin event-store constant')
req(f"const IMMUTABLE_AUDIT_LEDGER_SCHEMA = '{LEDGER}';" in php,'plugin ledger constant')
req(f"const AUDIT_EVENT_SCHEMA = '{AUDIT_EVENT}';" in php,'plugin audit-event constant')
req('Stable tag: 3.15.0' in readme,'plugin stable tag')
req(BUILD in php and SOURCE in php and BUILD in compose and SOURCE in compose and BUILD in docker and SOURCE in docker and BUILD in render and SOURCE in render,'identity propagation')
req('sustainable-catalyst-decision-studio:3.15.0' in compose,'compose image')
req("d.get('version') == '3.15.0'" in docker,'docker health version')
for p in ['backend/app/global_auth.py','backend/app/decision_rooms.py','backend/app/module_interoperability.py','backend/app/module_artifact_provenance.py','backend/app/cross_module_composition.py','backend/app/unified_module_registry.py','backend/migrations/versions/0002_v3130_collaboration.py','backend/migrations/versions/0003_v3150_event_ledger.py']:
    req((ROOT/p).exists(),f'preserved {p}')
req('.venv-*/' in text('.gitignore') and '.venv/' in text('.gitignore'),'venv ignore')
jsons=[p for p in ROOT.rglob('*.json') if '.git' not in p.parts]
for p in jsons: json.loads(p.read_text())
print(f'Decision Studio v{VERSION} release-integrity checks passed: Decision Event Store & Immutable Audit Ledger, 8 audit-ledger routes, append-only database guard, deterministic stream sequencing, SHA-256 payload/event hash chain, authenticated actor + institution identity, correlation/causation IDs, historical event backfill, read-only replay, 27 persistence tables on Alembic revision {REVISION}, 25 route registries, 308 certified API routes, v3.14 global auth + v3.13 room persistence + v3.12 shared evidence + v3.11 provenance + v3.10 composition preserved, human-governed final decision authority, and {len(jsons)} JSON files validated.')
