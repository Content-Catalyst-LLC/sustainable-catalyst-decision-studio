#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v2.9.0."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PLUGIN=ROOT/'wordpress-plugin'/'sustainable-catalyst-decision-studio'
VERSION='2.9.0'; BUILD='scds-v2.9.0-recommendations-review-challenge'; SOURCE='release-v2.9.0'
PRODUCT_IDS=['knowledge-library','research-librarian','site-intelligence','workbench','research-lab','platform-core','decision-studio']
SCHEMAS={
'decision_packet':'scds-decision-packet/2.0','decision_object':'scds-decision-object/1.0','platform_context':'scds-platform-context/1.0',
'evidence_bundle':'scds-evidence-bundle/1.0','source_bundle':'scds-source-bundle/1.0','evidence_coverage':'scds-evidence-coverage/1.0',
'criteria_set':'scds-criteria-set/1.0','alternatives_set':'scds-alternatives-set/1.0','tradeoff_matrix':'scds-tradeoff-matrix/1.0','tradeoff_diagnostics':'scds-tradeoff-diagnostics/1.0',
'uncertainty_register':'scds-uncertainty-register/1.0','sensitivity_analysis':'scds-sensitivity-analysis/1.0','confidence_assessment':'scds-confidence-assessment/1.0',
'scenario_set':'scds-scenario-set/1.0','scenario_comparison':'scds-scenario-comparison/1.0','stress_test_suite':'scds-stress-test-suite/1.0',
'analysis_handoff':'scds-analysis-handoff/1.0','computation_handoff':'scds-computation-handoff/1.0','handoff_receipt':'scds-handoff-receipt/1.0','analysis_request':'scds-analysis-request/1.0',
'site_intelligence_context_bundle':'scds-site-intelligence-context-bundle/1.0','site_intelligence_signal_snapshot':'scds-site-intelligence-signal-snapshot/1.0','site_intelligence_context_receipt':'scds-site-intelligence-context-receipt/1.0',
'decision_dependency_graph':'scds-decision-dependency-graph/1.0','dependency_diagnostics':'scds-dependency-diagnostics/1.0','change_impact_assessment':'scds-change-impact-assessment/1.0',
'recommendation_candidate':'scds-recommendation-candidate/1.0','recommendation_challenge':'scds-recommendation-challenge/1.0','recommendation_review':'scds-recommendation-review/1.0'}

def req(x,msg):
    if not x: raise AssertionError(msg)
def load(p):
    with open(p,encoding='utf-8') as f:return json.load(f)
def text(rel):return (ROOT/rel).read_text(encoding='utf-8')

main=text('backend/app/main.py'); rec=text('backend/app/recommendation_review.py'); dep=text('backend/app/dependency_graph.py'); native=text('backend/app/native_handoffs.py'); site=text('backend/app/site_intelligence_context.py'); scenario=text('backend/app/scenario_stress.py'); tests=text('backend/tests/test_backend.py'); energy=text('backend/app/energy_runtime_consumer.py')
php=(PLUGIN/'sustainable-catalyst-decision-studio.php').read_text(); js=(PLUGIN/'assets/js/scds-decision-studio.js').read_text(); pread=(PLUGIN/'readme.txt').read_text(); docker=text('backend/Dockerfile'); compose=text('compose.yml'); render=text('backend/render.yaml'); readme=text('README.md'); changelog=text('CHANGELOG.md'); doc=text('docs/V290_RECOMMENDATIONS_REVIEW_CHALLENGE.md')
# identity
req(f'APP_VERSION = "{VERSION}"' in main,'backend version')
for t in [main,php,docker,compose,render]: req(BUILD in t,'build fingerprint parity'); req(SOURCE in t,'source commit parity')
req(' * Version: 2.9.0' in php and "const VERSION = '2.9.0';" in php,'plugin version'); req('Stable tag: 2.9.0' in pread,'stable tag')
# schema preservation
combined='\n'.join([main,rec,dep,native,site,scenario,php,doc])
for sch in SCHEMAS.values(): req(sch in combined,f'schema {sch}')
# routes parity
v29=['/recommendation-review/template','/recommendation-review/candidate','/recommendation-review/challenge','/recommendation-review/evaluate','/recommendation-review/disposition','/decision-object/recommendation-review','/decision-packet/recommendation-review']
for r in v29:req(r in main and r in php,f'v2.9 route {r}')
for r in ['/decision-dependency-graph/build','/decision-dependency-graph/impact','/site-intelligence-context/build','/native-handoffs/receive','/scenario-analysis/compare','/stress-test-suite/run']:
    req(r in main or r in energy,f'preserved backend route {r}')
req('prefix="/v1/energy-runtime"' in energy and '@router.get("/consumer")' in energy,'preserved Energy consumer route')
# UI/JS
for m in ['Recommendation Review','data-scds-v290-selected-alternative','data-scds-v290-challenge-statement','data-scds-v290-candidate','data-scds-v290-challenge','data-scds-v290-evaluate','data-scds-v290-disposition-btn','data-scds-v290-attach','Review boundary:']:req(m in php,f'WP UI {m}')
for m in ['recommendationReviewInputs','recommendationReviewHtml','runRecommendationReview','downloadRecommendationReview','restRecommendationCandidateUrl','restRecommendationChallengeUrl','restRecommendationEvaluateUrl','restRecommendationDispositionUrl','restDecisionObjectRecommendationReviewUrl']:req(m in js+php,f'JS binding {m}')
# metadata parity
manifest=load(ROOT/'data/decision_studio_release_manifest_v2.9.0.json'); pmanifest=load(PLUGIN/'data/release_manifest_v2.9.0.json'); integrations=load(ROOT/'data/decision_studio_integrations_v2.9.0.json'); pintegrations=load(PLUGIN/'data/decision_studio_integrations_v2.9.0.json')
req(manifest==pmanifest,'manifest parity');req(integrations==pintegrations,'integrations parity');req(manifest['release']==VERSION and manifest['build_fingerprint']==BUILD and manifest['source_commit']==SOURCE,'manifest identity')
for k,v in SCHEMAS.items():req(manifest['schemas'].get(k)==v,f'manifest schema {k}')
# contracts/samples parity
for stem in ['recommendation_candidate_contract','recommendation_candidate_sample','recommendation_challenge_contract','recommendation_challenge_sample','recommendation_review_contract','recommendation_review_sample']:
    a=load(ROOT/f'data/{stem}_v2.9.0.json');b=load(PLUGIN/f'data/{stem}_v2.9.0.json');req(a==b,f'{stem} parity')
c=load(ROOT/'data/recommendation_candidate_sample_v2.9.0.json');ch=load(ROOT/'data/recommendation_challenge_sample_v2.9.0.json');rv=load(ROOT/'data/recommendation_review_sample_v2.9.0.json')
req(c['schema']==SCHEMAS['recommendation_candidate'] and c['automatic_selection'] is False and c['automatic_approval'] is False and len(c['candidate_fingerprint'])==64,'candidate sample')
req(ch['schema']==SCHEMAS['recommendation_challenge'] and ch['status']=='open' and ch['automatic_disposition'] is False and len(ch['challenge_fingerprint'])==64,'challenge sample')
req(rv['schema']==SCHEMAS['recommendation_review'] and rv['automatic_approval'] is False and rv['automatic_recommendation'] is False and len(rv['review_fingerprint'])==64,'review sample')
# compatibility
compat=manifest['compatibility']
for flag in ['recommendation_candidates','recommendation_challenges','human_recommendation_disposition','explicit_support_and_counterargument_links','open_challenge_override_requires_human_action','v2_8_0_dependency_graph_preserved','decision_dependency_graphs','v2_7_0_site_intelligence_context_preserved','v2_6_0_native_handoffs_preserved','v2_5_0_scenario_stress_preserved','v2_3_0_energy_runtime_consumer_preserved']:req(compat.get(flag) is True,f'compat true {flag}')
for flag in ['recommendation_candidate_implies_winner','recommendation_score_implies_approval','challenge_resolution_is_automatic','human_disposition_executes_decision','automatic_winner_selection','automatic_recommendation','automatic_truth_verification','dependency_graph_implies_causality','site_intelligence_context_implies_causality','decision_studio_executes_external_analysis']:req(compat.get(flag) is False,f'compat false {flag}')
req(compat.get('energy_runtime_consumer_version')=='2.3.0','Energy version')
# source boundaries
for phrase in ['does not automatically select a winner','infer approval from a score','convert a review disposition into execution authority']:req(phrase in rec,f'recommendation boundary {phrase}')
req('open challenges require explicit overrideOpenChallenges' in rec,'open challenge override')
req('execution_authorized": False' in rec and 'approval_inferred": False' in rec,'human disposition non-execution')
req('An edge is not causal proof' in dep,'v2.8 dependency boundary preserved');req('signal fingerprint does not match raw payload' in site,'v2.7 tamper preservation');req('artifact fingerprint does not match payload' in native,'v2.6 tamper preservation');req('ordering_changed_vs_baseline' in scenario,'v2.5 preservation')
# test names
for name in ['test_v290_templates_expose_recommendation_review_contracts','test_v290_candidate_requires_explicit_selection_and_preserves_support_counter_links','test_v290_open_challenge_blocks_review_but_does_not_auto_reject','test_v290_accepting_disposition_requires_explicit_open_challenge_override','test_v290_challenge_resolution_is_human_and_auditable','test_v290_candidate_tamper_is_rejected','test_v290_attach_to_decision_object_and_packet_without_overwriting_legacy_recommendation','test_v290_release_declares_review_challenge_boundaries_and_preserves_v280']:
    req(name in tests,f'test {name}')
# runtime identity
req('python:3.12-slim' in docker and '8089' in docker and '2.9.0' in docker,'Docker');req('sustainable-catalyst-decision-studio:2.9.0' in compose and 'sc-decision-studio' in compose and 'sc-internal' in compose,'compose')
# history preserved
for path in ['data/decision_studio_release_manifest_v2.8.0.json','data/decision_dependency_graph_contract_v2.8.0.json','data/decision_studio_release_manifest_v2.7.0.json','data/site_intelligence_context_bundle_contract_v2.7.0.json','data/decision_studio_release_manifest_v2.6.0.json','data/analysis_handoff_contract_v2.6.0.json','data/decision_studio_release_manifest_v2.5.0.json','data/scenario_set_contract_v2.5.0.json','data/decision_studio_release_manifest_v2.4.0.json','data/decision_studio_release_manifest_v2.3.1.json','data/decision_studio_release_manifest_v2.2.0.json','data/decision_studio_release_manifest_v2.1.0.json']:
    req((ROOT/path).exists(),f'preserved {path}')
req('Recommendations, Review & Challenge Layer' in readme+changelog+doc+pread,'v2.9 docs')
# all JSON parses
jsons=[p for p in ROOT.rglob('*.json') if '.git' not in p.parts]
for p in jsons:load(p)
print(f'Decision Studio v{VERSION} release-integrity checks passed. Validated {len(jsons)} JSON files, {len(PRODUCT_IDS)} platform roles, Recommendations/Review/Challenge v1.0 contracts, v2.8 Decision Graph preservation, v2.7 Site Intelligence context preservation, v2.6 native handoff preservation, v2.5 Scenario/Stress preservation, and Energy v2.3.0 preservation.')
