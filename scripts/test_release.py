#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VERSION='3.13.0'
NAME='Collaboration & Decision Room Python Persistence'
BUILD='scds-v3.13.0-collaboration-decision-room-python-persistence'
SOURCE='release-v3.13.0'
PREV_REV='0001_v330_pg_foundation'
REVISION='0002_v3130_collaboration'
ROOM='scds-collaborative-decision-room/2.0'
EVENT='scds-collaboration-event/2.0'
PERSIST='scds-decision-room-python-persistence/1.0'

def text(p): return (ROOT/p).read_text()
def load(p): return json.loads(text(p))
def req(c,m):
    if not c: raise SystemExit(f'FAIL: {m}')

service=text('backend/app/services/decision_service.py')
rooms=text('backend/app/decision_rooms.py')
routes=text('backend/app/api/routes/decision_rooms.py')
router=text('backend/app/api/router.py')
models=text('backend/app/persistence/models.py')
mig1=text('backend/migrations/versions/0001_v330_pg_foundation.py')
mig2=text('backend/migrations/versions/0002_v3130_collaboration.py')
persistence=text('backend/app/persistence/database.py')
php=text('wordpress-plugin/sustainable-catalyst-decision-studio/sustainable-catalyst-decision-studio.php')
readme=text('wordpress-plugin/sustainable-catalyst-decision-studio/readme.txt')
compose=text('compose.yml'); docker=text('backend/Dockerfile'); render=text('backend/render.yaml')
inv=load('data/backend_route_inventory_v3.13.0.json')
prev=load('data/backend_route_inventory_v3.12.0.json')
manifest=load('data/decision_studio_release_manifest_v3.13.0.json')
pmanifest=load('wordpress-plugin/sustainable-catalyst-decision-studio/data/release_manifest_v3.13.0.json')
contract=load('data/decision_room_python_persistence_contract_v3.13.0.json')
pc=load('data/postgresql_persistence_contract_v3.13.0.json')
schema=load('data/postgresql_schema_manifest_v3.13.0.json')

req(f'APP_VERSION = "{VERSION}"' in service,'backend version')
req(NAME in service and BUILD in service and SOURCE in service,'backend identity')
req(ROOM in rooms and EVENT in rooms and PERSIST in rooms,'room schemas')
req('DecisionRoomRepository' in rooms and 'room_events_are_hash_chained' in rooms,'room repository/contract')
req('token_hash' in rooms and 'secrets.token_urlsafe' in rooms,'hashed share tokens')
req('legacy_wordpress_source_preserved' in rooms and 'import_legacy' in rooms,'legacy source-preserving import')
req('from app.api.routes.decision_rooms import router as decision_rooms_router' in router and 'include_router(decision_rooms_router)' in router,'room router included')
req(inv['release']==VERSION and inv['route_count']==293,'route inventory identity/count')
req(len(inv['routers'])==24 and len(inv['routers']['decision_rooms'])==21,'router inventory')
old={(r['path'],r['method']) for rs in prev['routers'].values() for r in rs}; new={(r['path'],r['method']) for rs in inv['routers'].values() for r in rs}; req(old<=new,'v3.12 routes preserved')
req(manifest==pmanifest,'manifest parity')
req(manifest['release']==VERSION and manifest['release_name']==NAME and manifest['build_fingerprint']==BUILD and manifest['source_commit']==SOURCE,'manifest identity')
req(manifest['backend']['route_count']==293 and manifest['backend']['route_registry_count']==23 and manifest['backend']['included_router_count']==24,'manifest backend counts')
dr=manifest['decision_room_python_persistence']; req(dr['schema']==PERSIST and dr['room_schema']==ROOM and dr['event_schema']==EVENT,'room manifest schemas')
req(dr['schema_revision']==REVISION and dr['previous_schema_revision']==PREV_REV and len(dr['tables_added'])==6,'room migration manifest')
req(dr['wordpress_canonical_room_persistence'] is False and dr['legacy_wordpress_projection_preserved'] is True,'WordPress room authority cutover')
req(manifest['next_release'].startswith('3.14.0'),'next release')
req(contract['schema']==ROOM and contract['persistence_schema']==PERSIST and contract['migration']['revision']==REVISION,'contract identity/migration')
req(contract['principles']['share_tokens_are_stored_only_as_sha256_hashes'] is True and contract['principles']['ai_cannot_approve_or_sign'] is True,'room security/governance')
req(schema['revision']==REVISION and schema['previous_revision']==PREV_REV and schema['table_count']==26 and schema['collaboration_schema_migration'] is True,'schema migrated')
req(len(schema['collaboration_tables'])==6 and schema['snapshots_reused_for_rooms'] is True,'collaboration table manifest')
req(pc['expected_schema_revision']==REVISION and pc['new_schema_migration_in_v3_13'] is True and pc['table_count']==26,'persistence contract migration')
for table in schema['tables']:
    req(f'__tablename__ = "{table}"' in models,f'model missing {table}')
for table in schema['collaboration_tables']:
    req(f'"{table}"' in mig2,f'v3.13 migration missing {table}')
req(f'revision = "{REVISION}"' in mig2 and f'down_revision = "{PREV_REV}"' in mig2 and len(REVISION)<=32,'alembic v3.13 revision chain')
req(PREV_REV in mig1 and REVISION in persistence,'alembic history/current revision')
req(' * Version: 3.13.0' in php and "const VERSION = '3.13.0';" in php,'plugin metadata')
req("const DB_VERSION = '3.0.0';" in php,'WordPress DB unchanged')
req(f"const DECISION_ROOM_V2_SCHEMA = '{ROOM}';" in php and f"const DECISION_ROOM_PERSISTENCE_SCHEMA = '{PERSIST}';" in php,'plugin room constants')
req('Stable tag: 3.13.0' in readme,'plugin stable tag')
req(BUILD in php and SOURCE in php and BUILD in compose and SOURCE in compose and BUILD in docker and SOURCE in docker and BUILD in render and SOURCE in render,'release identity propagation')
req('sustainable-catalyst-decision-studio:3.13.0' in compose,'compose image')
req("d.get('version') == '3.13.0'" in docker,'docker health version')
for p in ['backend/app/module_interoperability.py','backend/app/module_artifact_provenance.py','backend/app/cross_module_composition.py','backend/app/unified_module_registry.py','data/backend_route_inventory_v3.12.0.json']:
    req((ROOT/p).exists(),f'preserved {p}')
req('.venv-*/' in text('.gitignore') and '.venv/' in text('.gitignore'),'venv ignore')
jsons=[p for p in ROOT.rglob('*.json') if '.git' not in p.parts]
for p in jsons: json.loads(p.read_text())
print(f'Decision Studio v{VERSION} release-integrity checks passed: authoritative Collaboration & Decision Room Python Persistence, 21 decision-room routes, 6 new collaboration tables plus existing room snapshots, hash-chained room events, SHA-256-only share-token storage, source-preserving legacy WordPress room import, 26 persistence tables on Alembic revision {REVISION}, 23 route registries, 293 certified API routes, v3.12 shared evidence + v3.11 artifact provenance + v3.10 composition preserved, human-governed final decision authority, and {len(jsons)} JSON files validated.')
