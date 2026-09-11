#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v2.1.0."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "wordpress-plugin" / "sustainable-catalyst-decision-studio"
VERSION = "2.1.0"
BUILD = "scds-v2.1.0-unified-decision-object-platform-context-foundation"
SOURCE = "release-v2.1.0"
PACKET = "scds-decision-packet/2.0"
OBJECT = "scds-decision-object/1.0"
CONTEXT = "scds-platform-context/1.0"
MIGRATION = "scds-decision-object-migration/1.0"
PRODUCT_IDS = ["knowledge-library","research-librarian","site-intelligence","workbench","research-lab","platform-core","decision-studio"]

def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)

def load(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)

main=(ROOT/'backend/app/main.py').read_text()
model=(ROOT/'backend/app/decision_object.py').read_text()
php=(PLUGIN/'sustainable-catalyst-decision-studio.php').read_text()
js=(PLUGIN/'assets/js/scds-decision-studio.js').read_text()
render=(ROOT/'backend/render.yaml').read_text()
build=(ROOT/'scripts/build_release.sh').read_text()
readme=(ROOT/'README.md').read_text()
changelog=(ROOT/'CHANGELOG.md').read_text()
doc=(ROOT/'docs/V210_UNIFIED_DECISION_OBJECT_PLATFORM_CONTEXT_FOUNDATION.md').read_text()
plugin_readme=(PLUGIN/'readme.txt').read_text()

require(f'APP_VERSION = "{VERSION}"' in main, 'backend version')
require(BUILD in main and BUILD in php and BUILD in render, 'fingerprint parity')
require(SOURCE in main and SOURCE in php and SOURCE in render, 'source parity')
require(' * Version: 2.1.0' in php and "const VERSION = '2.1.0';" in php, 'plugin version')
require('Stable tag: 2.1.0' in plugin_readme, 'stable tag')
require('VERSION="2.1.0"' in build, 'build version')
for schema in [OBJECT, CONTEXT, MIGRATION, PACKET]:
    require(schema in main+model+php+doc, f'schema parity {schema}')
for path in ['/decision-object/template','/platform-context/template','/decision-object/from-packet','/decision-object/normalize','/decision-object/context','/decision-object/to-packet','/decision-packet/decision-object']:
    require(path in main and path in php, f'route parity {path}')
for marker in ['data-scds-decision-object-build','data-scds-decision-object-template','data-scds-platform-context-template','data-scds-decision-object-project','data-scds-decision-object-download','Decision Object']:
    require(marker in php, f'WordPress UI {marker}')
for marker in ['runDecisionObject','decisionObjectHtml','downloadDecisionObject','restDecisionObjectFromPacketUrl','restDecisionObjectToPacketUrl']:
    require(marker in js+php, f'JS/WordPress binding {marker}')
for product in PRODUCT_IDS:
    require(product in model and product in php, f'platform product {product}')

manifest=load(ROOT/'data/decision_studio_release_manifest_v2.1.0.json')
pmanifest=load(PLUGIN/'data/release_manifest_v2.1.0.json')
integrations=load(ROOT/'data/decision_studio_integrations_v2.1.0.json')
pintegrations=load(PLUGIN/'data/decision_studio_integrations_v2.1.0.json')
contract=load(ROOT/'data/decision_object_contract_v2.1.0.json')
pcontract=load(PLUGIN/'data/decision_object_contract_v2.1.0.json')
context_contract=load(ROOT/'data/platform_context_contract_v2.1.0.json')
pcontext_contract=load(PLUGIN/'data/platform_context_contract_v2.1.0.json')
sample=load(ROOT/'data/decision_object_sample_v2.1.0.json')
psample=load(PLUGIN/'data/decision_object_sample_v2.1.0.json')
require(manifest==pmanifest,'manifest parity')
require(integrations==pintegrations,'integration parity')
require(contract==pcontract,'decision object contract parity')
require(context_contract==pcontext_contract,'platform context contract parity')
require(sample==psample,'decision object sample parity')
require(manifest['release']==VERSION and manifest['schemas']['decision_packet']==PACKET,'manifest identity')
require(manifest['schemas']['decision_object']==OBJECT and manifest['schemas']['platform_context']==CONTEXT,'manifest schemas')
require([x['id'] for x in integrations['platform_context']]==PRODUCT_IDS,'platform context order')
require(sample['schema']==OBJECT and sample['platform_context']['schema']==CONTEXT,'sample schemas')
require(sample['provenance']['source_packet_fingerprint'],'sample source fingerprint')
require(sample['compatibility']['packet_schema_breaking_changes'] is False,'additive compatibility')
require('v2.1.0' in readme+changelog+doc and 'Unified Decision Object' in readme+changelog+doc,'documentation')

# Preserve v2.0.x foundations and full capability chain.
for path in ['data/decision_studio_release_manifest_v2.0.1.json','data/module_navigation_contract_v2.0.1.json','data/connected_decision_platform_contract_v2.0.0.json','data/connected_decision_platform_sample_v2.0.0.json']:
    require((ROOT/path).exists(), f'preserved {path}')
for marker in ['scds-catalyst-module-navigation/1.0','scds-catalyst-module-handoff/1.0','scds-connected-decision-platform/2.0','scds-decision-governance/1.0','scds-scenario-studio/1.0','scds-collaborative-decision-room/1.0','scds-institutional-decision-pack/1.0','scds-decision-publication/1.0','scds-outcome-monitoring/1.0','scds-public-api/1.0','scds-release-readiness/1.0']:
    require(marker in main+php, f'preserved capability {marker}')

json_files=[p for p in ROOT.rglob('*.json') if '.git' not in p.parts]
for path in json_files:
    load(path)
print(f'Decision Studio v{VERSION} release-integrity checks passed. Validated {len(json_files)} JSON files, {len(PRODUCT_IDS)} platform roles, and reversible Decision Object foundation markers.')
