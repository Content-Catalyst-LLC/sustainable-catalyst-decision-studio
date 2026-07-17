#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v2.0.1."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "wordpress-plugin" / "sustainable-catalyst-decision-studio"
VERSION = "2.0.1"
BUILD = "scds-v2.0.1-catalyst-module-navigation-handoff-repair"
SOURCE = "release-v2.0.1"
PACKET = "scds-decision-packet/2.0"
NAV = "scds-catalyst-module-navigation/1.0"
HANDOFF = "scds-catalyst-module-handoff/1.0"
MODULE_IDS = ["catalyst-canvas","catalyst-data","catalyst-analytics-r","global-impact-catalyst","catalyst-narrative-risk","catalyst-finance","catalyst-grit"]

def require(condition: bool, message: str) -> None:
    if not condition: raise AssertionError(message)

def load(path: Path):
    with path.open(encoding="utf-8") as handle: return json.load(handle)

main=(ROOT/'backend/app/main.py').read_text(); php=(PLUGIN/'sustainable-catalyst-decision-studio.php').read_text(); js=(PLUGIN/'assets/js/scds-decision-studio.js').read_text(); css=(PLUGIN/'assets/css/scds-decision-studio.css').read_text(); render=(ROOT/'backend/render.yaml').read_text(); build=(ROOT/'scripts/build_release.sh').read_text(); readme=(ROOT/'README.md').read_text(); changelog=(ROOT/'CHANGELOG.md').read_text(); doc=(ROOT/'docs/V201_CATALYST_MODULE_NAVIGATION_HANDOFF_REPAIR.md').read_text(); plugin_readme=(PLUGIN/'readme.txt').read_text()
require(f'APP_VERSION = "{VERSION}"' in main, 'backend version')
require(BUILD in main and BUILD in php and BUILD in render, 'fingerprint parity')
require(SOURCE in main and SOURCE in php and SOURCE in render, 'source parity')
require(' * Version: 2.0.1' in php and "const VERSION = '2.0.1';" in php, 'plugin version')
require('Stable tag: 2.0.1' in plugin_readme, 'stable tag')
require('VERSION="2.0.1"' in build, 'build version')
require(NAV in main and NAV in php and HANDOFF in main and HANDOFF in php and HANDOFF in js, 'navigation/handoff schemas')
require('/integrations/module-navigation' in main and '/integrations/module-navigation' in php, 'navigation endpoints')
for module_id in MODULE_IDS:
    require(module_id in main and module_id in php and module_id in js, f'module {module_id}')
for marker in ['data-scds-send-module','data-scds-import-module-action','data-scds-module-handoff-status','Catalyst Modules','Route configured · Adapter ready']:
    require(marker in php, f'PHP UI {marker}')
for marker in ['prepareModuleHandoff','focusModuleImport','browser_local_storage','scds_return','moduleHandoffStoragePrefix']:
    require(marker in js, f'JS handoff {marker}')
for marker in ['scds-catalyst-module-grid','scds-module-handoff-status','scds-mini-button-primary']:
    require(marker in css, f'CSS {marker}')
manifest=load(ROOT/'data/decision_studio_release_manifest_v2.0.1.json'); pmanifest=load(PLUGIN/'data/release_manifest_v2.0.1.json'); integrations=load(ROOT/'data/decision_studio_integrations_v2.0.1.json'); pintegrations=load(PLUGIN/'data/decision_studio_integrations_v2.0.1.json'); contract=load(ROOT/'data/module_navigation_contract_v2.0.1.json'); pcontract=load(PLUGIN/'data/module_navigation_contract_v2.0.1.json'); sample=load(ROOT/'data/module_navigation_sample_v2.0.1.json'); psample=load(PLUGIN/'data/module_navigation_sample_v2.0.1.json')
require(manifest==pmanifest,'manifest parity'); require(integrations==pintegrations,'integration parity'); require(contract==pcontract,'contract parity'); require(sample==psample,'sample parity')
require(manifest['release']==VERSION and manifest['schemas']['decision_packet']==PACKET,'manifest identity')
require([m['id'] for m in integrations['modules']]==MODULE_IDS,'module order')
require(sample['handoff']['automatic_external_delivery'] is False and sample['handoff']['human_action_required'] is True,'handoff boundary')
require('v2.0.1' in readme+changelog+doc and 'Catalyst Module Navigation' in changelog+doc,'documentation')
# Preserve v2.0.0 connected platform assets and full capability chain.
for path in ['data/connected_decision_platform_contract_v2.0.0.json','data/connected_decision_platform_sample_v2.0.0.json','data/decision_studio_release_manifest_v2.0.0.json']:
    require((ROOT/path).exists(), f'preserved {path}')
for marker in ['scds-platform-artifact/1.0','scds-decision-governance/1.0','scds-scenario-studio/1.0','scds-collaborative-decision-room/1.0','scds-institutional-decision-pack/1.0','scds-decision-publication/1.0','scds-outcome-monitoring/1.0','scds-public-api/1.0','scds-release-readiness/1.0','scds-connected-decision-platform/2.0']:
    require(marker in main+php, f'preserved capability {marker}')
json_files=[p for p in ROOT.rglob('*.json') if '.git' not in p.parts]
for path in json_files: load(path)
print(f'Decision Studio v{VERSION} release-integrity checks passed. Validated {len(json_files)} JSON files and seven Catalyst module routes.')
