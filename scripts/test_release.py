#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v2.2.0."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "wordpress-plugin" / "sustainable-catalyst-decision-studio"
VERSION = "2.2.0"
BUILD = "scds-v2.2.0-evidence-source-bundles"
SOURCE = "release-v2.2.0"
PACKET = "scds-decision-packet/2.0"
OBJECT = "scds-decision-object/1.0"
CONTEXT = "scds-platform-context/1.0"
EVIDENCE = "scds-evidence-bundle/1.0"
SOURCE_BUNDLE = "scds-source-bundle/1.0"
COVERAGE = "scds-evidence-coverage/1.0"
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
php=(PLUGIN/'sustainable-catalyst-decision-studio.php').read_text()
js=(PLUGIN/'assets/js/scds-decision-studio.js').read_text()
docker=(ROOT/'backend/Dockerfile').read_text()
compose=(ROOT/'compose.yml').read_text()
render=(ROOT/'backend/render.yaml').read_text()
readme=(ROOT/'README.md').read_text()
changelog=(ROOT/'CHANGELOG.md').read_text()
doc=(ROOT/'docs/V220_EVIDENCE_SOURCE_BUNDLES.md').read_text()
plugin_readme=(PLUGIN/'readme.txt').read_text()

require(f'APP_VERSION = "{VERSION}"' in main, 'backend version')
for text in [main, php, docker, compose, render]:
    require(BUILD in text, 'build fingerprint parity')
    require(SOURCE in text, 'source commit parity')
require(' * Version: 2.2.0' in php and "const VERSION = '2.2.0';" in php, 'plugin version')
require('Stable tag: 2.2.0' in plugin_readme, 'stable tag')
for schema in [PACKET, OBJECT, CONTEXT, EVIDENCE, SOURCE_BUNDLE, COVERAGE]:
    require(schema in main+php+doc+evidence_model+model, f'schema parity {schema}')

routes=['/source-bundle/template','/source-bundle/build','/evidence-bundle/template','/evidence-bundle/build','/evidence-bundle/merge','/decision-object/evidence','/decision-packet/evidence-bundle']
for route in routes:
    require(route in main and route in php, f'route parity {route}')
for marker in ['data-scds-source-bundle-build','data-scds-evidence-bundle-build','data-scds-evidence-attach','data-scds-evidence-download','Evidence &amp; Sources']:
    require(marker in php, f'WordPress UI {marker}')
for marker in ['runEvidenceBundle','evidenceBundleHtml','downloadEvidenceBundle','restEvidenceBundleBuildUrl','restDecisionObjectEvidenceUrl']:
    require(marker in js+php, f'JS/WordPress binding {marker}')

manifest=load(ROOT/'data/decision_studio_release_manifest_v2.2.0.json')
pmanifest=load(PLUGIN/'data/release_manifest_v2.2.0.json')
integrations=load(ROOT/'data/decision_studio_integrations_v2.2.0.json')
pintegrations=load(PLUGIN/'data/decision_studio_integrations_v2.2.0.json')
ev_contract=load(ROOT/'data/evidence_bundle_contract_v2.2.0.json')
pev_contract=load(PLUGIN/'data/evidence_bundle_contract_v2.2.0.json')
src_contract=load(ROOT/'data/source_bundle_contract_v2.2.0.json')
psrc_contract=load(PLUGIN/'data/source_bundle_contract_v2.2.0.json')
ev_sample=load(ROOT/'data/evidence_bundle_sample_v2.2.0.json')
pev_sample=load(PLUGIN/'data/evidence_bundle_sample_v2.2.0.json')
src_sample=load(ROOT/'data/source_bundle_sample_v2.2.0.json')
psrc_sample=load(PLUGIN/'data/source_bundle_sample_v2.2.0.json')

require(manifest==pmanifest,'manifest parity')
require(integrations==pintegrations,'integration parity')
require(ev_contract==pev_contract,'evidence contract parity')
require(src_contract==psrc_contract,'source contract parity')
require(ev_sample==pev_sample,'evidence sample parity')
require(src_sample==psrc_sample,'source sample parity')
require(manifest['release']==VERSION and manifest['schemas']['decision_packet']==PACKET,'manifest identity')
require(manifest['schemas']['decision_object']==OBJECT and manifest['schemas']['platform_context']==CONTEXT,'v2.1 schema preservation')
require(manifest['schemas']['evidence_bundle']==EVIDENCE and manifest['schemas']['source_bundle']==SOURCE_BUNDLE and manifest['schemas']['evidence_coverage']==COVERAGE,'v2.2 schemas')
require(ev_sample['source_bundle']['schema']==SOURCE_BUNDLE and ev_sample['coverage']['schema']==COVERAGE,'sample nested schemas')
require(ev_sample['coverage']['citation_coverage_percent']==100.0,'sample coverage')
require(ev_sample['review']['status']=='needs_review','human review boundary')
require(manifest['compatibility']['automatic_truth_verification'] is False,'no automatic truth verification')
require([x['id'] for x in integrations['platform_context']]==PRODUCT_IDS,'platform context preserved')

# Runtime / hosting identity
require('python:3.12-slim' in docker and '8089' in docker and '2.2.0' in docker, 'Docker runtime identity')
require('sustainable-catalyst-decision-studio:2.2.0' in compose and 'sc-decision-studio' in compose and 'sc-internal' in compose, 'Contabo compose identity')

# Preserve previous release contracts.
for path in ['data/decision_studio_release_manifest_v2.1.0.json','data/decision_object_contract_v2.1.0.json','data/platform_context_contract_v2.1.0.json','data/decision_studio_release_manifest_v2.0.1.json']:
    require((ROOT/path).exists(), f'preserved {path}')
for marker in ['scds-decision-object/1.0','scds-platform-context/1.0','scds-connected-decision-platform/2.0','scds-catalyst-module-navigation/1.0']:
    require(marker in main+php+model, f'preserved capability {marker}')
require('Evidence & Source Bundles' in readme+changelog+doc+plugin_readme,'documentation')

json_files=[p for p in ROOT.rglob('*.json') if '.git' not in p.parts]
for path in json_files:
    load(path)
print(f'Decision Studio v{VERSION} release-integrity checks passed. Validated {len(json_files)} JSON files, {len(PRODUCT_IDS)} platform roles, and Evidence/Source Bundle v1.0 contracts.')
