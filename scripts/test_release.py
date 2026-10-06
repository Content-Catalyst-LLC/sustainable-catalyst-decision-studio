#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v3.2.0."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PLUGIN=ROOT/'wordpress-plugin'/'sustainable-catalyst-decision-studio'
VERSION='3.2.0'
BUILD='scds-v3.2.0-decision-kernel-module-contract-foundation'
SOURCE='release-v3.2.0'

def req(value, message):
    if not value: raise AssertionError(message)
def load(path):
    with open(path,encoding='utf-8') as f: return json.load(f)
def text(rel): return (ROOT/rel).read_text(encoding='utf-8')

main=text('backend/app/main.py')
service=text('backend/app/services/decision_service.py')
kernel=text('backend/app/decision_kernel.py')
api_router=text('backend/app/api/router.py')
php=(PLUGIN/'sustainable-catalyst-decision-studio.php').read_text(encoding='utf-8')
readme=(PLUGIN/'readme.txt').read_text(encoding='utf-8')
docker=text('backend/Dockerfile'); compose=text('compose.yml'); render=text('backend/render.yaml')
inv=load(ROOT/'data/backend_route_inventory_v3.2.0.json')
manifest=load(ROOT/'data/decision_studio_release_manifest_v3.2.0.json')
pmanifest=load(PLUGIN/'data/release_manifest_v3.2.0.json')
registry=load(ROOT/'data/decision_module_registry_v3.2.0.json')

req('include_router(api_router)' in main,'main composition router')
req('@app.get' not in main and '@app.post' not in main,'main contains endpoint decorators')
req(len(main.splitlines()) <= 25,'main is not composition-only')
req(f'APP_VERSION = "{VERSION}"' in service,'service version')
req(BUILD in service and SOURCE in service,'service identity')
req('production_request_guard' in service,'request guard preserved')
req('decision_kernel_foundation' in service,'kernel foundation release flag')
req('from app.energy_runtime_consumer import router as energy_runtime_consumer_router' in api_router,'energy runtime router preserved')
req('decision_kernel_router' in api_router,'decision kernel router mounted')

route_dir=ROOT/'backend/app/api/routes'
router_modules=sorted(p for p in route_dir.glob('*.py') if p.name!='__init__.py')
req(len(router_modules)==12,'expected 12 route registry modules')
route_text='\n'.join(p.read_text(encoding='utf-8') for p in router_modules)
for group, routes in inv['routers'].items():
    if group=='energy_runtime': continue
    for route in routes:
        req(repr(route['path']) in route_text,f"missing route {route['path']}")
req(inv['route_count']==182 and inv['legacy_route_count']==176,'certified route counts')
req(len(inv['routers']['decision_kernel'])==6,'decision kernel routes')

req(manifest==pmanifest,'release manifest parity')
req(manifest['release']==VERSION and manifest['build_fingerprint']==BUILD and manifest['source_commit']==SOURCE,'manifest identity')
req(manifest['migration']=={'database':False,'wordpress_authority':False,'schema_breaking_changes':False},'migration-free release')
req(manifest['backend']['route_count']==182 and manifest['backend']['route_registry_count']==12,'manifest backend counts')
req(manifest['decision_kernel']['module_count']==4,'manifest module count')
req(manifest['decision_kernel']['final_decision_authority']=='human-governed','human governed authority')

req(registry['module_count']==4,'registry module count')
req({m['module_id'] for m in registry['modules']}=={'canvas','finance','narrative-risk','global-impact'},'required module ids')
for m in registry['modules']:
    req(m['module_contract_schema']=='scds-decision-module-contract/1.0',f"module contract schema {m['module_id']}")
finance=next(m for m in registry['modules'] if m['module_id']=='finance')
req(finance['providers']['compute_authority']=='workbench','finance compute authority')
for phrase in ['modules_extend_kernel_objects_not_fork_them','final_decision_authority_is_human_governed','DECISION_MODULE_CONTRACT_SCHEMA']:
    req(phrase in kernel,f'kernel principle {phrase}')

req(' * Version: 3.2.0' in php and "const VERSION = '3.2.0';" in php,'plugin release metadata')
req("const DB_VERSION = '3.0.0';" in php,'DB version must remain 3.0.0')
req('Stable tag: 3.2.0' in readme,'plugin stable tag')
for runtime in [docker,compose,render]: req(BUILD in runtime and SOURCE in runtime,'runtime identity parity')
req('sustainable-catalyst-decision-studio:3.2.0' in compose,'compose image version')
req("d.get('version') == '3.2.0'" in docker,'Docker health version')

# Preserve v3.1 decomposition and v3.0+ analytical domains.
for path in [
    'data/backend_route_inventory_v3.1.0.json','backend/app/connected_decision_intelligence.py','backend/app/recommendation_review.py',
    'backend/app/dependency_graph.py','backend/app/site_intelligence_context.py','backend/app/native_handoffs.py','backend/app/scenario_stress.py','backend/app/energy_runtime_consumer.py']:
    req((ROOT/path).exists(),f'preserved {path}')

jsons=[p for p in ROOT.rglob('*.json') if '.git' not in p.parts]
for p in jsons: load(p)
print(f'Decision Studio v{VERSION} release-integrity checks passed: Decision Kernel + 4 first-class module contracts, 12 route registries, 182 certified API routes, no DB/WordPress authority migration, and {len(jsons)} JSON files validated.')
