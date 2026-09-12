#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v2.3.1."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "wordpress-plugin" / "sustainable-catalyst-decision-studio"
VERSION = "2.3.1"
BUILD = "scds-v2.3.1-criteria-alternatives-tradeoff-matrix"
SOURCE = "release-v2.3.1"
PACKET = "scds-decision-packet/2.0"
OBJECT = "scds-decision-object/1.0"
CONTEXT = "scds-platform-context/1.0"
EVIDENCE = "scds-evidence-bundle/1.0"
SOURCE_BUNDLE = "scds-source-bundle/1.0"
COVERAGE = "scds-evidence-coverage/1.0"
CRITERIA = "scds-criteria-set/1.0"
ALTERNATIVES = "scds-alternatives-set/1.0"
MATRIX = "scds-tradeoff-matrix/1.0"
DIAGNOSTICS = "scds-tradeoff-diagnostics/1.0"
PRODUCT_IDS = ["knowledge-library","research-librarian","site-intelligence","workbench","research-lab","platform-core","decision-studio"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)

main=(ROOT/'backend/app/main.py').read_text()
model=(ROOT/'backend/app/decision_object.py').read_text()
evidence_model=(ROOT/'backend/app/evidence_bundle.py').read_text()
tradeoff_model=(ROOT/'backend/app/tradeoff_matrix.py').read_text()
energy_model=(ROOT/'backend/app/energy_runtime_consumer.py').read_text()
energy_test=(ROOT/'backend/tests/test_energy_runtime_consumer.py').read_text()
energy_doc=(ROOT/'ENERGY_RUNTIME_CONSUMER_2.3.0.md').read_text()
php=(PLUGIN/'sustainable-catalyst-decision-studio.php').read_text()
js=(PLUGIN/'assets/js/scds-decision-studio.js').read_text()
docker=(ROOT/'backend/Dockerfile').read_text()
compose=(ROOT/'compose.yml').read_text()
render=(ROOT/'backend/render.yaml').read_text()
readme=(ROOT/'README.md').read_text()
changelog=(ROOT/'CHANGELOG.md').read_text()
doc=(ROOT/'docs/V231_CRITERIA_ALTERNATIVES_TRADEOFF_MATRIX.md').read_text()
plugin_readme=(PLUGIN/'readme.txt').read_text()

require(f'APP_VERSION = "{VERSION}"' in main, 'backend version')
for text in [main, php, docker, compose, render]:
    require(BUILD in text, 'build fingerprint parity')
    require(SOURCE in text, 'source commit parity')
require(' * Version: 2.3.1' in php and "const VERSION = '2.3.1';" in php, 'plugin version')
require('Stable tag: 2.3.1' in plugin_readme, 'stable tag')
for schema in [PACKET, OBJECT, CONTEXT, EVIDENCE, SOURCE_BUNDLE, COVERAGE, CRITERIA, ALTERNATIVES, MATRIX, DIAGNOSTICS]:
    require(schema in main+php+doc+tradeoff_model+evidence_model+model, f'schema parity {schema}')

routes=['/criteria/template','/criteria/build','/alternatives/template','/alternatives/build','/tradeoff-matrix/template','/tradeoff-matrix/build','/decision-object/tradeoffs','/decision-packet/tradeoff-matrix']
for route in routes:
    require(route in main and route in php, f'route parity {route}')
for marker in ['data-scds-criteria-build','data-scds-alternatives-build','data-scds-tradeoff-build','data-scds-tradeoff-attach','data-scds-tradeoff-download','Tradeoff Matrix']:
    require(marker in php, f'WordPress UI {marker}')
for marker in ['runTradeoffMatrix','tradeoffMatrixHtml','downloadTradeoffMatrix','restTradeoffMatrixBuildUrl','restDecisionObjectTradeoffsUrl']:
    require(marker in js+php, f'JS/WordPress binding {marker}')

manifest=load(ROOT/'data/decision_studio_release_manifest_v2.3.1.json')
pmanifest=load(PLUGIN/'data/release_manifest_v2.3.1.json')
integrations=load(ROOT/'data/decision_studio_integrations_v2.3.1.json')
pintegrations=load(PLUGIN/'data/decision_studio_integrations_v2.3.1.json')
contracts=[]
for stem in ['criteria_set_contract','alternatives_set_contract','tradeoff_matrix_contract','tradeoff_diagnostics_contract','criteria_set_sample','alternatives_set_sample','tradeoff_matrix_sample']:
    a=load(ROOT/f'data/{stem}_v2.3.1.json')
    b=load(PLUGIN/f'data/{stem}_v2.3.1.json')
    require(a==b, f'{stem} parity')
    contracts.append(a)

require(manifest==pmanifest,'manifest parity')
require(integrations==pintegrations,'integration parity')
require(manifest['release']==VERSION and manifest['schemas']['decision_packet']==PACKET,'manifest identity')
require(manifest['schemas']['decision_object']==OBJECT and manifest['schemas']['platform_context']==CONTEXT,'v2.1 schema preservation')
require(manifest['schemas']['evidence_bundle']==EVIDENCE and manifest['schemas']['source_bundle']==SOURCE_BUNDLE and manifest['schemas']['evidence_coverage']==COVERAGE,'v2.2 schema preservation')
require(manifest['schemas']['criteria_set']==CRITERIA and manifest['schemas']['alternatives_set']==ALTERNATIVES and manifest['schemas']['tradeoff_matrix']==MATRIX and manifest['schemas']['tradeoff_diagnostics']==DIAGNOSTICS,'v2.3 schemas')
sample=load(ROOT/'data/tradeoff_matrix_sample_v2.3.1.json')
require(sample['criteria_set']['schema']==CRITERIA and sample['alternatives_set']['schema']==ALTERNATIVES,'sample nested schemas')
require(sample['diagnostics']['schema']==DIAGNOSTICS and sample['diagnostics']['matrix_coverage_percent']==100.0,'sample diagnostics')
require(sample['review']['status']=='needs_review','human review boundary')
require(manifest['compatibility']['automatic_winner_selection'] is False,'no automatic winner selection')
require(manifest['compatibility']['automatic_recommendation'] is False,'no automatic recommendation')
require(manifest['compatibility']['v2_3_0_energy_runtime_consumer_preserved'] is True,'Energy v2.3.0 runtime consumer preservation')
require(manifest['compatibility']['energy_runtime_consumer_version']=='2.3.0','Energy consumer component version')
for marker in ["CONSUMER_VERSION = '2.3.0'", "/v1/energy-runtime", "sc-energy-runtime-decision-studio-handoff/1.0"]:
    require(marker in energy_model+energy_doc+main, f'Energy runtime preservation {marker}')
require('test_consume_builds_ephemeral_receipt' in energy_test,'Energy runtime regression test preserved')
require('energy_runtime_consumer_router' in main,'Energy runtime router registered')
require("'energy_systems_runtime_consumer'=>true" in php and "'energy_runtime_consumer_version'=>'2.3.0'" in php,'WordPress release manifest declares Energy preservation')
require([x['id'] for x in integrations['platform_context']]==PRODUCT_IDS,'platform context preserved')

require('python:3.12-slim' in docker and '8089' in docker and '2.3.1' in docker, 'Docker runtime identity')
require('sustainable-catalyst-decision-studio:2.3.1' in compose and 'sc-decision-studio' in compose and 'sc-internal' in compose, 'Contabo compose identity')

for path in ['data/decision_studio_release_manifest_v2.2.0.json','data/evidence_bundle_contract_v2.2.0.json','data/source_bundle_contract_v2.2.0.json','data/decision_studio_release_manifest_v2.1.0.json','data/decision_object_contract_v2.1.0.json','data/platform_context_contract_v2.1.0.json','data/decision_studio_release_manifest_v2.0.1.json']:
    require((ROOT/path).exists(), f'preserved {path}')
for marker in ['scds-evidence-bundle/1.0','scds-source-bundle/1.0','scds-decision-object/1.0','scds-platform-context/1.0','scds-connected-decision-platform/2.0']:
    require(marker in main+php+model+evidence_model, f'preserved capability {marker}')
require('Criteria, Alternatives & Tradeoff Matrix' in readme+changelog+doc+plugin_readme,'documentation')

json_files=[p for p in ROOT.rglob('*.json') if '.git' not in p.parts]
for path in json_files:
    load(path)
print(f'Decision Studio v{VERSION} release-integrity checks passed. Validated {len(json_files)} JSON files, {len(PRODUCT_IDS)} platform roles, Criteria/Alternatives/Tradeoff Matrix v1.0 contracts, and preserved Energy Runtime Consumer v2.3.0.')
