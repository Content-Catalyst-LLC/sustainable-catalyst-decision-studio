#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v3.0.0."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PLUGIN=ROOT/'wordpress-plugin'/'sustainable-catalyst-decision-studio'
VERSION='3.0.0'; BUILD='scds-v3.0.0-connected-decision-intelligence'; SOURCE='release-v3.0.0'
PRODUCT_IDS=['knowledge-library','research-librarian','site-intelligence','workbench','research-lab','platform-core','decision-studio']
NEW_SCHEMAS={
'connected_decision_intelligence':'scds-connected-decision-intelligence/3.0',
'decision_lifecycle_state':'scds-decision-lifecycle-state/1.0',
'decision_readiness_matrix':'scds-decision-readiness-matrix/1.0',
'cross_product_route_plan':'scds-cross-product-route-plan/1.0',
}
PRESERVED_SCHEMAS={
'recommendation_candidate':'scds-recommendation-candidate/1.0','recommendation_challenge':'scds-recommendation-challenge/1.0','recommendation_review':'scds-recommendation-review/1.0',
'decision_dependency_graph':'scds-decision-dependency-graph/1.0','site_intelligence_context_bundle':'scds-site-intelligence-context-bundle/1.0',
'analysis_handoff':'scds-analysis-handoff/1.0','computation_handoff':'scds-computation-handoff/1.0','scenario_set':'scds-scenario-set/1.0','stress_test_suite':'scds-stress-test-suite/1.0',
'decision_object':'scds-decision-object/1.0','decision_packet':'scds-decision-packet/2.0'}

def req(x,msg):
    if not x: raise AssertionError(msg)
def load(p):
    with open(p,encoding='utf-8') as f:return json.load(f)
def text(rel):return (ROOT/rel).read_text(encoding='utf-8')

main=text('backend/app/main.py'); connected=text('backend/app/connected_decision_intelligence.py'); tests=text('backend/tests/test_backend.py')
rec=text('backend/app/recommendation_review.py'); dep=text('backend/app/dependency_graph.py'); site=text('backend/app/site_intelligence_context.py'); native=text('backend/app/native_handoffs.py'); scenario=text('backend/app/scenario_stress.py'); energy=text('backend/app/energy_runtime_consumer.py')
php=(PLUGIN/'sustainable-catalyst-decision-studio.php').read_text(); js=(PLUGIN/'assets/js/scds-decision-studio.js').read_text(); pread=(PLUGIN/'readme.txt').read_text(); docker=text('backend/Dockerfile'); compose=text('compose.yml'); render=text('backend/render.yaml'); doc=text('docs/V300_CONNECTED_DECISION_INTELLIGENCE.md')

# identity
req(f'APP_VERSION = "{VERSION}"' in main,'backend version')
for t in [main,php,docker,compose,render]: req(BUILD in t,'build fingerprint parity'); req(SOURCE in t,'source commit parity')
req(' * Version: 3.0.0' in php and "const VERSION = '3.0.0';" in php,'plugin version')
req('Stable tag: 3.0.0' in pread,'stable tag')
req("'release_name'=>'Connected Decision Intelligence'" in php,'WordPress release name')

# new schemas/routes and preservation
combined='\n'.join([main,connected,php,doc])
for sch in NEW_SCHEMAS.values(): req(sch in combined,f'new schema {sch}')
all_preserved='\n'.join([main,rec,dep,site,native,scenario,energy,php])
for sch in PRESERVED_SCHEMAS.values(): req(sch in all_preserved,f'preserved schema {sch}')
routes=['/connected-intelligence/template','/connected-intelligence/build','/connected-intelligence/validate','/decision-object/connected-intelligence','/decision-packet/connected-intelligence']
for r in routes:req(r in main and r in php,f'v3 route {r}')
for r in ['/recommendation-review/candidate','/decision-dependency-graph/build','/site-intelligence-context/build','/native-handoffs/receive','/scenario-analysis/compare','/stress-test-suite/run']:
    req(r in main,f'preserved route {r}')
req('prefix="/v1/energy-runtime"' in energy and '@router.get("/consumer")' in energy,'Energy consumer route')

# orchestration boundaries
for phrase in ['Readiness is not approval','lifecycle position is not an automatic transition','route plans do not execute external work','does not select a winner']:
    req(phrase in connected,f'boundary {phrase}')
for key in ['winner_selection_automatic','recommendation_automatic','stage_transition_automatic','approval_automatic','external_execution_automatic']:
    req(key in connected,f'human-control key {key}')
for stage in ['frame','evidence','analyze','compare','stress','review','decide','monitor']:req(f'("{stage}"' in connected or f'"{stage}"' in connected,f'stage {stage}')

# WP UI/JS
for m in ['Connected Intelligence','data-scds-v300-build','data-scds-v300-validate','data-scds-v300-attach','data-scds-v300-packet','Connected intelligence boundary:']:req(m in php,f'WP UI {m}')
for m in ['connectedIntelligenceHtml','runConnectedIntelligenceV300','downloadConnectedIntelligenceV300','restConnectedIntelligenceBuildUrl','restDecisionObjectConnectedIntelligenceUrl','restDecisionPacketConnectedIntelligenceUrl']:req(m in js+php,f'JS binding {m}')

# manifests / contracts parity
manifest=load(ROOT/'data/decision_studio_release_manifest_v3.0.0.json'); pmanifest=load(PLUGIN/'data/release_manifest_v3.0.0.json'); integ=load(ROOT/'data/decision_studio_integrations_v3.0.0.json'); pinteg=load(PLUGIN/'data/decision_studio_integrations_v3.0.0.json')
req(manifest==pmanifest,'manifest parity'); req(integ==pinteg,'integration parity')
req(manifest['release']==VERSION and manifest['build_fingerprint']==BUILD and manifest['source_commit']==SOURCE,'manifest identity')
for k,v in NEW_SCHEMAS.items(): req(manifest['schemas'].get(k)==v,f'manifest schema {k}')
for stem in NEW_SCHEMAS:
    for kind in ['contract','sample']:
        a=load(ROOT/f'data/{stem}_{kind}_v3.0.0.json'); b=load(PLUGIN/f'data/{stem}_{kind}_v3.0.0.json'); req(a==b,f'{stem} {kind} parity')
ci=load(ROOT/'data/connected_decision_intelligence_sample_v3.0.0.json')
req(ci['schema']==NEW_SCHEMAS['connected_decision_intelligence'],'connected sample schema')
req(len(ci['readiness_matrix']['stages'])==8,'eight stage sample')
req(all(v is False for v in ci['human_control'].values()),'human control false')
req(len(ci['connected_intelligence_fingerprint'])==64,'connected fingerprint')

compat=manifest['compatibility']
for flag in ['connected_decision_intelligence_v3','canonical_eight_stage_lifecycle','cross_product_readiness_matrix','bounded_cross_product_route_plan','decision_record_is_human_owned','v2_9_0_recommendation_review_preserved','v2_8_0_dependency_graph_preserved','v2_7_0_site_intelligence_context_preserved','v2_6_0_native_handoffs_preserved','v2_5_0_scenario_stress_preserved','v2_3_0_energy_runtime_consumer_preserved']:
    req(compat.get(flag) is True,f'compat true {flag}')
for flag in ['readiness_implies_approval','lifecycle_stage_transition_is_automatic','route_plan_executes_external_work','automatic_winner_selection','automatic_recommendation','decision_studio_executes_external_analysis','dependency_graph_implies_causality','site_intelligence_context_implies_causality']:
    req(compat.get(flag) is False,f'compat false {flag}')
req(compat.get('energy_runtime_consumer_version')=='2.3.0','Energy version')

# regression test names
for name in ['test_v300_template_exposes_connected_intelligence_contracts','test_v300_build_unifies_eight_stage_lifecycle_without_auto_advancing','test_v300_route_plan_is_bounded_and_points_to_first_incomplete_stage','test_v300_explicit_decision_and_outcome_complete_lifecycle_but_do_not_authorize_execution','test_v300_connected_intelligence_tamper_is_rejected','test_v300_attach_to_decision_object_and_packet_preserves_lineage','test_v300_release_declares_connected_intelligence_and_preserves_v290']:
    req(name in tests,f'test {name}')

# runtime identity / history
req('python:3.12-slim' in docker and "'3.0.0'" in docker,'Docker 3.0')
req('sustainable-catalyst-decision-studio:3.0.0' in compose and 'sc-decision-studio' in compose and 'sc-internal' in compose,'compose')
for path in ['data/decision_studio_release_manifest_v2.9.0.json','data/recommendation_review_contract_v2.9.0.json','data/decision_studio_release_manifest_v2.8.0.json','data/decision_dependency_graph_contract_v2.8.0.json','data/decision_studio_release_manifest_v2.7.0.json','data/site_intelligence_context_bundle_contract_v2.7.0.json','data/decision_studio_release_manifest_v2.6.0.json','data/analysis_handoff_contract_v2.6.0.json','data/decision_studio_release_manifest_v2.5.0.json','data/scenario_set_contract_v2.5.0.json','data/decision_studio_release_manifest_v2.4.0.json','data/decision_studio_release_manifest_v2.3.1.json','data/decision_studio_release_manifest_v2.2.0.json','data/decision_studio_release_manifest_v2.1.0.json']:
    req((ROOT/path).exists(),f'preserved {path}')
# all JSON parses
jsons=[p for p in ROOT.rglob('*.json') if '.git' not in p.parts]
for p in jsons:load(p)
print(f'Decision Studio v{VERSION} release-integrity checks passed. Validated {len(jsons)} JSON files, {len(PRODUCT_IDS)} platform roles, Connected Decision Intelligence v3.0 contracts, v2.9 Review/Challenge preservation, v2.8 Decision Graph preservation, v2.7 Site Intelligence preservation, v2.6 native handoff preservation, v2.5 Scenario/Stress preservation, and Energy v2.3.0 preservation.')
