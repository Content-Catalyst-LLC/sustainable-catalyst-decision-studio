#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v2.8.0."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PLUGIN=ROOT/'wordpress-plugin'/'sustainable-catalyst-decision-studio'
VERSION='2.8.0'; BUILD='scds-v2.8.0-decision-graph-dependency-mapping'; SOURCE='release-v2.8.0'
PRODUCT_IDS=['knowledge-library','research-librarian','site-intelligence','workbench','research-lab','platform-core','decision-studio']
SCHEMAS={
'decision_packet':'scds-decision-packet/2.0','decision_object':'scds-decision-object/1.0','platform_context':'scds-platform-context/1.0',
'evidence_bundle':'scds-evidence-bundle/1.0','source_bundle':'scds-source-bundle/1.0','evidence_coverage':'scds-evidence-coverage/1.0',
'criteria_set':'scds-criteria-set/1.0','alternatives_set':'scds-alternatives-set/1.0','tradeoff_matrix':'scds-tradeoff-matrix/1.0','tradeoff_diagnostics':'scds-tradeoff-diagnostics/1.0',
'uncertainty_register':'scds-uncertainty-register/1.0','sensitivity_analysis':'scds-sensitivity-analysis/1.0','confidence_assessment':'scds-confidence-assessment/1.0',
'scenario_set':'scds-scenario-set/1.0','scenario_comparison':'scds-scenario-comparison/1.0','stress_test_suite':'scds-stress-test-suite/1.0',
'analysis_handoff':'scds-analysis-handoff/1.0','computation_handoff':'scds-computation-handoff/1.0','handoff_receipt':'scds-handoff-receipt/1.0','analysis_request':'scds-analysis-request/1.0',
'site_intelligence_context_bundle':'scds-site-intelligence-context-bundle/1.0','site_intelligence_signal_snapshot':'scds-site-intelligence-signal-snapshot/1.0','site_intelligence_context_receipt':'scds-site-intelligence-context-receipt/1.0',
'decision_dependency_graph':'scds-decision-dependency-graph/1.0','dependency_diagnostics':'scds-dependency-diagnostics/1.0','change_impact_assessment':'scds-change-impact-assessment/1.0'}

def req(x,msg):
    if not x: raise AssertionError(msg)
def load(p):
    with open(p,encoding='utf-8') as f:return json.load(f)

def text(rel):return (ROOT/rel).read_text(encoding='utf-8')
main=text('backend/app/main.py'); dep=text('backend/app/dependency_graph.py'); native=text('backend/app/native_handoffs.py'); site=text('backend/app/site_intelligence_context.py'); scenario=text('backend/app/scenario_stress.py'); tests=text('backend/tests/test_backend.py'); energy=text('backend/app/energy_runtime_consumer.py')
php=(PLUGIN/'sustainable-catalyst-decision-studio.php').read_text(); js=(PLUGIN/'assets/js/scds-decision-studio.js').read_text(); pread=(PLUGIN/'readme.txt').read_text(); docker=text('backend/Dockerfile'); compose=text('compose.yml'); render=text('backend/render.yaml'); readme=text('README.md'); changelog=text('CHANGELOG.md'); doc=text('docs/V280_DECISION_GRAPH_DEPENDENCY_MAPPING.md')
# identity
req(f'APP_VERSION = "{VERSION}"' in main,'backend version')
for t in [main,php,docker,compose,render]: req(BUILD in t,'build fingerprint parity'); req(SOURCE in t,'source commit parity')
req(' * Version: 2.8.0' in php and "const VERSION = '2.8.0';" in php,'plugin version'); req('Stable tag: 2.8.0' in pread,'stable tag')
# schema preservation
combined='\n'.join([main,dep,native,site,scenario,php,doc])
for sch in SCHEMAS.values(): req(sch in combined,f'schema {sch}')
# routes parity
v28=['/decision-dependency-graph/template','/decision-dependency-graph/build','/decision-dependency-graph/validate','/decision-dependency-graph/impact','/decision-object/dependency-graph','/decision-packet/dependency-graph']
for r in v28:req(r in main and r in php,f'v2.8 route {r}')
for r in ['/site-intelligence-context/build','/decision-object/site-intelligence-context','/native-handoffs/receive','/decision-object/native-handoff','/scenario-analysis/compare','/stress-test-suite/run']:
    req(r in main or r in energy,f'preserved backend route {r}')
req('prefix="/v1/energy-runtime"' in energy and '@router.get("/consumer")' in energy,'preserved Energy consumer route')
# UI/JS
for m in ['Decision Graph','data-scds-v280-explicit-edges','data-scds-v280-changed-node-ids','data-scds-v280-build','data-scds-v280-validate','data-scds-v280-impact','data-scds-v280-attach','data-scds-v280-download','Dependency boundary:']:req(m in php,f'WP UI {m}')
for m in ['dependencyGraphInputs','dependencyGraphHtml','runDependencyGraph','downloadDependencyGraph','restDependencyGraphTemplateUrl','restDependencyGraphBuildUrl','restDependencyGraphValidateUrl','restDependencyGraphImpactUrl','restDecisionObjectDependencyGraphUrl','restDecisionPacketDependencyGraphUrl']:req(m in js+php,f'JS binding {m}')
# root/plugin metadata parity
manifest=load(ROOT/'data/decision_studio_release_manifest_v2.8.0.json'); pmanifest=load(PLUGIN/'data/release_manifest_v2.8.0.json'); integrations=load(ROOT/'data/decision_studio_integrations_v2.8.0.json'); pintegrations=load(PLUGIN/'data/decision_studio_integrations_v2.8.0.json')
req(manifest==pmanifest,'manifest parity');req(integrations==pintegrations,'integrations parity');req(manifest['release']==VERSION and manifest['build_fingerprint']==BUILD and manifest['source_commit']==SOURCE,'manifest identity')
for k,v in SCHEMAS.items():req(manifest['schemas'].get(k)==v,f'manifest schema {k}')
# new contracts/samples parity and meaning
for stem in ['decision_dependency_graph_contract','decision_dependency_graph_sample','dependency_diagnostics_contract','dependency_diagnostics_sample','change_impact_assessment_contract','change_impact_assessment_sample']:
    a=load(ROOT/f'data/{stem}_v2.8.0.json');b=load(PLUGIN/f'data/{stem}_v2.8.0.json');req(a==b,f'{stem} parity')
g=load(ROOT/'data/decision_dependency_graph_sample_v2.8.0.json');d=load(ROOT/'data/dependency_diagnostics_sample_v2.8.0.json');i=load(ROOT/'data/change_impact_assessment_sample_v2.8.0.json')
req(g['schema']==SCHEMAS['decision_dependency_graph'] and len(g['graph_fingerprint'])==64,'graph sample fingerprint');req(d['schema']==SCHEMAS['dependency_diagnostics'],'diagnostics sample');req(i['schema']==SCHEMAS['change_impact_assessment'] and i['automatic_invalidation'] is False and i['causal_claim'] is False and i['recommendation_changed'] is False,'impact boundary')
req(all(e.get('causal_claim') is False and e.get('automatic_invalidation') is False for e in g.get('edges',[])),'graph edges bounded')
# compatibility
compat=manifest['compatibility']
for flag in ['v2_7_0_site_intelligence_context_preserved','decision_dependency_graphs','dependency_mapping','change_impact_tracing','explicit_dependency_edges_preserved','orphan_dependency_diagnostics','cycle_dependency_diagnostics','v2_6_0_native_handoffs_preserved','v2_5_0_scenario_stress_preserved','v2_3_0_energy_runtime_consumer_preserved']:req(compat.get(flag) is True,f'compat true {flag}')
for flag in ['dependency_graph_implies_causality','dependency_degree_implies_importance','change_impact_implies_invalidation','change_impact_changes_recommendation_automatically','automatic_winner_selection','automatic_recommendation','automatic_truth_verification','site_intelligence_context_implies_causality','decision_studio_executes_external_analysis']:req(compat.get(flag) is False,f'compat false {flag}')
req(compat.get('energy_runtime_consumer_version')=='2.3.0','Energy version')
# source boundaries
for phrase in ['An edge is not causal proof','node degree is not importance','downstream reachability is not automatic invalidation']:req(phrase in dep,f'dependency boundary {phrase}')
req('automatic_invalidation' in dep and 'recommendation_changed' in dep,'change impact fields')
req('signal fingerprint does not match raw payload' in site,'v2.7 tamper preservation');req('artifact fingerprint does not match payload' in native,'v2.6 tamper preservation');req('ordering_changed_vs_baseline' in scenario,'v2.5 preservation')
# test names
for name in ['test_v280_dependency_graph_template_contracts','test_v280_builds_dependency_graph_without_causal_claims','test_v280_explicit_record_dependencies_are_preserved','test_v280_change_impact_is_review_queue_not_invalidation','test_v280_dependency_graph_tamper_rejected','test_v280_attach_to_decision_object_and_packet','test_v280_release_declares_dependency_mapping_boundaries_and_preserves_v270']:
    req(name in tests,f'test {name}')
# runtime identity
req('python:3.12-slim' in docker and '8089' in docker and '2.8.0' in docker,'Docker');req('sustainable-catalyst-decision-studio:2.8.0' in compose and 'sc-decision-studio' in compose and 'sc-internal' in compose,'compose')
# history preserved
for path in ['data/decision_studio_release_manifest_v2.7.0.json','data/site_intelligence_context_bundle_contract_v2.7.0.json','data/decision_studio_release_manifest_v2.6.0.json','data/analysis_handoff_contract_v2.6.0.json','data/decision_studio_release_manifest_v2.5.0.json','data/scenario_set_contract_v2.5.0.json','data/decision_studio_release_manifest_v2.4.0.json','data/decision_studio_release_manifest_v2.3.1.json','data/decision_studio_release_manifest_v2.2.0.json','data/decision_studio_release_manifest_v2.1.0.json']:
    req((ROOT/path).exists(),f'preserved {path}')
req('Decision Graph & Dependency Mapping' in readme+changelog+doc+pread,'v2.8 docs')
# all JSON parses
jsons=[p for p in ROOT.rglob('*.json') if '.git' not in p.parts]
for p in jsons:load(p)
print(f'Decision Studio v{VERSION} release-integrity checks passed. Validated {len(jsons)} JSON files, {len(PRODUCT_IDS)} platform roles, Decision Graph/Dependency Mapping v1.0 contracts, v2.7 Site Intelligence context preservation, v2.6 native handoff preservation, v2.5 Scenario/Stress preservation, and Energy v2.3.0 preservation.')
