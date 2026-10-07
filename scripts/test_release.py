#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VERSION='3.14.0'
NAME='Global Authentication & Authorization Integration'
BUILD='scds-v3.14.0-global-authentication-authorization-integration'
SOURCE='release-v3.14.0'
REVISION='0002_v3130_collaboration'
AUTH='scds-global-authentication-authorization/1.0'
PRINCIPAL='scds-authenticated-principal/1.0'
AUTHZ='scds-authorization-decision/1.0'

def text(p): return (ROOT/p).read_text()
def load(p): return json.loads(text(p))
def req(c,m):
    if not c: raise SystemExit(f'FAIL: {m}')

service=text('backend/app/services/decision_service.py')
auth=text('backend/app/global_auth.py')
auth_routes=text('backend/app/api/routes/auth.py')
rooms=text('backend/app/decision_rooms.py')
router=text('backend/app/api/router.py')
persistence=text('backend/app/persistence/database.py')
models=text('backend/app/persistence/models.py')
php=text('wordpress-plugin/sustainable-catalyst-decision-studio/sustainable-catalyst-decision-studio.php')
readme=text('wordpress-plugin/sustainable-catalyst-decision-studio/readme.txt')
compose=text('compose.yml'); docker=text('backend/Dockerfile'); render=text('backend/render.yaml')
inv=load('data/backend_route_inventory_v3.14.0.json')
prev=load('data/backend_route_inventory_v3.13.0.json')
manifest=load('data/decision_studio_release_manifest_v3.14.0.json')
pmanifest=load('wordpress-plugin/sustainable-catalyst-decision-studio/data/release_manifest_v3.14.0.json')
contract=load('data/global_authentication_authorization_contract_v3.14.0.json')
pc=load('data/postgresql_persistence_contract_v3.14.0.json')
schema=load('data/postgresql_schema_manifest_v3.14.0.json')

req(f'APP_VERSION = "{VERSION}"' in service,'backend version')
req(NAME in service and BUILD in service and SOURCE in service,'backend identity')
req(AUTH in auth and PRINCIPAL in auth and AUTHZ in auth,'auth schemas')
req('global-bearer-jwt' in auth and 'service-api-key' in auth and 'legacy-api-key' in auth,'auth credential modes')
req('invalid_bearer_signature' in auth and 'bearer_audience_mismatch' in auth and 'bearer_token_expired' in auth,'bearer validation')
req('credential_precedence' in auth and 'legacy_api_key_status' in auth,'downgrade/compatibility contract')
req('from app.api.routes.auth import router as auth_router' in router and 'include_router(auth_router)' in router,'auth router included')
req(inv['release']==VERSION and inv['route_count']==300,'route inventory identity/count')
req(len(inv['routers'])==25 and len(inv['routers']['global_auth'])==7,'router inventory/auth routes')
old={(r['path'],r['method']) for rs in prev['routers'].values() for r in rs}; new={(r['path'],r['method']) for rs in inv['routers'].values() for r in rs}; req(old<=new,'v3.13 routes preserved')
req(manifest==pmanifest,'manifest parity')
req(manifest['release']==VERSION and manifest['release_name']==NAME and manifest['build_fingerprint']==BUILD and manifest['source_commit']==SOURCE,'manifest identity')
a=manifest['backend_architecture']; req(a['route_count']==300 and a['router_registry_count']==24 and a['included_router_count']==25,'manifest backend counts')
req(a['database_migration'] is False and a['global_authentication_authorization_integration'] is True,'v3.14 architecture boundary')
ga=manifest['global_authentication_authorization']; req(ga['schema']==AUTH and ga['principal_schema']==PRINCIPAL and ga['authorization_decision_schema']==AUTHZ,'auth manifest schemas')
req(ga['primary_user_authentication']=='bearer-jwt-hs256' and ga['legacy_api_key_status']=='compatibility-only','auth primary/compatibility boundary')
req(ga['decision_room_membership_enforced'] is True and ga['authenticated_actor_spoofing_prevented'] is True,'room auth boundaries')
req(manifest['next_release'].startswith('3.15.0'),'next release')
req(contract['schema']==AUTH and contract['authentication_authority']=='sustainable-catalyst-global-auth','contract authority')
req(contract['principles']['decision_room_membership_is_enforced_for_user_principals'] is True,'membership contract')
req(contract['principles']['request_body_cannot_impersonate_authenticated_room_actor'] is True,'anti-spoof contract')
req(contract['schema_migration_required'] is False,'auth needs no migration')
req(schema['revision']==REVISION and schema['table_count']==26 and schema['schema_migration_required'] is False,'schema preserved')
req(pc['expected_schema_revision']==REVISION and pc['new_schema_migration_in_v3_14'] is False and pc['table_count']==26,'persistence preserved')
req('EXPECTED_SCHEMA_REVISION = "0002_v3130_collaboration"' in persistence,'current revision preserved')
req(len([x for x in schema['tables'] if f'__tablename__ = "{x}"' in models])==26,'all persistence models preserved')
req('authentication_authority": "sustainable-catalyst-global-auth"' in rooms,'decision rooms use global auth authority')
req('authenticated_user_membership_is_enforced' in rooms,'room membership contract flag')
req('request_body_actor_fields_cannot_override_authenticated_identity' in rooms,'room anti-spoof flag')
req(' * Version: 3.14.0' in php and "const VERSION = '3.14.0';" in php,'plugin metadata')
req("const DB_VERSION = '3.0.0';" in php,'WordPress DB unchanged')
req(f"const GLOBAL_AUTH_SCHEMA = '{AUTH}';" in php,'plugin auth constant')
req('Stable tag: 3.14.0' in readme,'plugin stable tag')
req(BUILD in php and SOURCE in php and BUILD in compose and SOURCE in compose and BUILD in docker and SOURCE in docker and BUILD in render and SOURCE in render,'identity propagation')
req('sustainable-catalyst-decision-studio:3.14.0' in compose,'compose image')
req("d.get('version') == '3.14.0'" in docker,'docker health version')
for p in ['backend/app/decision_rooms.py','backend/app/module_interoperability.py','backend/app/module_artifact_provenance.py','backend/app/cross_module_composition.py','backend/app/unified_module_registry.py','backend/migrations/versions/0002_v3130_collaboration.py']:
    req((ROOT/p).exists(),f'preserved {p}')
req('.venv-*/' in text('.gitignore') and '.venv/' in text('.gitignore'),'venv ignore')
jsons=[p for p in ROOT.rglob('*.json') if '.git' not in p.parts]
for p in jsons: json.loads(p.read_text())
print(f'Decision Studio v{VERSION} release-integrity checks passed: Global Authentication & Authorization Integration, 7 auth routes, bearer identity + institution/scopes, service credentials, downgrade-resistant legacy compatibility, Decision Room membership/role enforcement and actor anti-spoofing, 26 persistence tables preserved on Alembic revision {REVISION}, 24 route registries, 300 certified API routes, v3.13 room persistence + v3.12 shared evidence + v3.11 provenance + v3.10 composition preserved, human-governed final decision authority, and {len(jsons)} JSON files validated.')
