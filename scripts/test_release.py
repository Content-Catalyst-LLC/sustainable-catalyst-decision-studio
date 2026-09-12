#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v2.5.0."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "wordpress-plugin" / "sustainable-catalyst-decision-studio"
VERSION = "2.5.0"
BUILD = "scds-v2.5.0-scenario-comparison-stress-testing"
SOURCE = "release-v2.5.0"
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
UNCERTAINTY = "scds-uncertainty-register/1.0"
SENSITIVITY = "scds-sensitivity-analysis/1.0"
CONFIDENCE = "scds-confidence-assessment/1.0"
SCENARIO_SET = "scds-scenario-set/1.0"
SCENARIO_COMPARISON = "scds-scenario-comparison/1.0"
STRESS_SUITE = "scds-stress-test-suite/1.0"
PRODUCT_IDS = ["knowledge-library","research-librarian","site-intelligence","workbench","research-lab","platform-core","decision-studio"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)

main=(ROOT/'backend/app/main.py').read_text()
scenario_model=(ROOT/'backend/app/scenario_stress.py').read_text()
model=(ROOT/'backend/app/decision_object.py').read_text()
evidence_model=(ROOT/'backend/app/evidence_bundle.py').read_text()
tradeoff_model=(ROOT/'backend/app/tradeoff_matrix.py').read_text()
uncertainty_model=(ROOT/'backend/app/uncertainty_confidence.py').read_text()
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
doc=(ROOT/'docs/V250_SCENARIO_COMPARISON_STRESS_TESTING.md').read_text()
plugin_readme=(PLUGIN/'readme.txt').read_text()

require(f'APP_VERSION = "{VERSION}"' in main, 'backend version')
for text in [main, php, docker, compose, render]:
    require(BUILD in text, 'build fingerprint parity')
    require(SOURCE in text, 'source commit parity')
require(' * Version: 2.5.0' in php and "const VERSION = '2.5.0';" in php, 'plugin version')
require('Stable tag: 2.5.0' in plugin_readme, 'stable tag')
for schema in [PACKET, OBJECT, CONTEXT, EVIDENCE, SOURCE_BUNDLE, COVERAGE, CRITERIA, ALTERNATIVES, MATRIX, DIAGNOSTICS, UNCERTAINTY, SENSITIVITY, CONFIDENCE, SCENARIO_SET, SCENARIO_COMPARISON, STRESS_SUITE]:
    require(schema in main+php+doc+scenario_model+uncertainty_model+tradeoff_model+evidence_model+model, f'schema parity {schema}')

routes=[
    '/scenario-set/template','/scenario-set/build',
    '/scenario-analysis/template','/scenario-analysis/compare',
    '/stress-test-suite/template','/stress-test-suite/run',
    '/decision-object/scenario-stress','/decision-packet/scenario-stress'
]
for route in routes:
    require(route in main and route in php, f'route parity {route}')
for marker in ['data-scds-v250-scenarios','data-scds-v250-stress-config','data-scds-v250-scenario-set','data-scds-v250-compare','data-scds-v250-stress','data-scds-v250-attach','data-scds-v250-download','Scenario Comparison &amp; Stress Testing']:
    require(marker in php, f'WordPress UI {marker}')
for marker in ['runScenarioStress','scenarioStressHtml','downloadScenarioStress','restScenarioAnalysisCompareUrl','restStressTestSuiteRunUrl','restDecisionObjectScenarioStressUrl']:
    require(marker in js+php, f'JS/WordPress binding {marker}')

manifest=load(ROOT/'data/decision_studio_release_manifest_v2.5.0.json')
pmanifest=load(PLUGIN/'data/release_manifest_v2.5.0.json')
integrations=load(ROOT/'data/decision_studio_integrations_v2.5.0.json')
pintegrations=load(PLUGIN/'data/decision_studio_integrations_v2.5.0.json')
require(manifest==pmanifest,'manifest parity')
require(integrations==pintegrations,'integration parity')
require(manifest['release']==VERSION and manifest['schemas']['decision_packet']==PACKET,'manifest identity')
require(manifest['schemas']['decision_object']==OBJECT and manifest['schemas']['platform_context']==CONTEXT,'v2.1 schema preservation')
require(manifest['schemas']['evidence_bundle']==EVIDENCE and manifest['schemas']['source_bundle']==SOURCE_BUNDLE and manifest['schemas']['evidence_coverage']==COVERAGE,'v2.2 schema preservation')
require(manifest['schemas']['criteria_set']==CRITERIA and manifest['schemas']['alternatives_set']==ALTERNATIVES and manifest['schemas']['tradeoff_matrix']==MATRIX and manifest['schemas']['tradeoff_diagnostics']==DIAGNOSTICS,'v2.3.1 schema preservation')
require(manifest['schemas']['uncertainty_register']==UNCERTAINTY and manifest['schemas']['sensitivity_analysis']==SENSITIVITY and manifest['schemas']['confidence_assessment']==CONFIDENCE,'v2.4 schema preservation')
require(manifest['schemas']['scenario_set']==SCENARIO_SET and manifest['schemas']['scenario_comparison']==SCENARIO_COMPARISON and manifest['schemas']['stress_test_suite']==STRESS_SUITE,'v2.5 schemas')

for stem in ['scenario_set_contract','scenario_comparison_contract','stress_test_suite_contract','scenario_set_sample','scenario_comparison_sample','stress_test_suite_sample']:
    a=load(ROOT/f'data/{stem}_v2.5.0.json')
    b=load(PLUGIN/f'data/{stem}_v2.5.0.json')
    require(a==b, f'{stem} parity')

sample_set=load(ROOT/'data/scenario_set_sample_v2.5.0.json')
sample_comp=load(ROOT/'data/scenario_comparison_sample_v2.5.0.json')
sample_stress=load(ROOT/'data/stress_test_suite_sample_v2.5.0.json')
require(sample_set['schema']==SCENARIO_SET and sample_set['diagnostics']['scenario_count']>=3,'scenario set sample')
require(sample_comp['schema']==SCENARIO_COMPARISON and sample_comp['diagnostics']['max_score_swing']>0,'scenario comparison sample')
require('recommended_option' not in sample_comp and 'winner' not in sample_comp,'no automatic scenario winner fields')
require(sample_stress['schema']==STRESS_SUITE and sample_stress['diagnostics']['test_count']>0,'stress suite sample')
require('approval' in sample_stress['boundary'].lower(),'stress-test approval boundary')

compat=manifest['compatibility']
require(compat['automatic_winner_selection'] is False,'no automatic winner selection')
require(compat['automatic_recommendation'] is False,'no automatic recommendation')
require(compat['confidence_is_probability_of_correctness'] is False,'confidence not correctness probability')
require(compat['scenario_likelihood_inference'] is False,'no scenario likelihood inference')
require(compat['stress_test_pass_implies_approval'] is False,'stress pass not approval')
require(compat['v2_3_0_energy_runtime_consumer_preserved'] is True,'Energy v2.3.0 runtime consumer preservation')
require(compat['energy_runtime_consumer_version']=='2.3.0','Energy consumer component version')
for marker in ["CONSUMER_VERSION = '2.3.0'", "/v1/energy-runtime", "sc-energy-runtime-decision-studio-handoff/1.0"]:
    require(marker in energy_model+energy_doc+main, f'Energy runtime preservation {marker}')
require('test_consume_builds_ephemeral_receipt' in energy_test,'Energy runtime regression test preserved')
require('energy_runtime_consumer_router' in main,'Energy runtime router registered')
require("'energy_systems_runtime_consumer'=>true" in php and "'energy_runtime_consumer_version'=>'2.3.0'" in php,'WordPress release manifest declares Energy preservation')
require([x['id'] for x in integrations['platform_context']]==PRODUCT_IDS,'platform context preserved')

require('python:3.12-slim' in docker and '8089' in docker and '2.5.0' in docker, 'Docker runtime identity')
require('sustainable-catalyst-decision-studio:2.5.0' in compose and 'sc-decision-studio' in compose and 'sc-internal' in compose, 'Contabo compose identity')

for path in [
    'data/decision_studio_release_manifest_v2.4.0.json','data/confidence_assessment_contract_v2.4.0.json',
    'data/decision_studio_release_manifest_v2.3.1.json','data/tradeoff_matrix_contract_v2.3.1.json',
    'data/decision_studio_release_manifest_v2.2.0.json','data/evidence_bundle_contract_v2.2.0.json','data/source_bundle_contract_v2.2.0.json',
    'data/decision_studio_release_manifest_v2.1.0.json','data/decision_object_contract_v2.1.0.json','data/platform_context_contract_v2.1.0.json',
    'data/decision_studio_release_manifest_v2.0.1.json']:
    require((ROOT/path).exists(), f'preserved {path}')
for marker in [SCENARIO_SET,SCENARIO_COMPARISON,STRESS_SUITE,UNCERTAINTY,SENSITIVITY,CONFIDENCE,MATRIX,EVIDENCE,OBJECT,CONTEXT]:
    require(marker in main+php+scenario_model+uncertainty_model+tradeoff_model+evidence_model+model, f'preserved capability {marker}')
require('Scenario Comparison & Stress Testing' in readme+changelog+doc+plugin_readme,'documentation')
require('ordering_changed_vs_baseline' in scenario_model,'scenario ordering diagnostics')
require('failure_codes' in scenario_model,'stress failure diagnostics')
require('scenario_likelihood_inference' in main+php and 'stress_test_pass_implies_approval' in main+php,'human-control markers')
require('automatic_winner_selection' in main+php and 'automatic_recommendation' in main+php,'human control markers')

json_files=[p for p in ROOT.rglob('*.json') if '.git' not in p.parts]
for path in json_files:
    load(path)
print(f'Decision Studio v{VERSION} release-integrity checks passed. Validated {len(json_files)} JSON files, {len(PRODUCT_IDS)} platform roles, Scenario/Stress v1.0 contracts, preserved v2.4 uncertainty/confidence, and preserved Energy Runtime Consumer v2.3.0.')
