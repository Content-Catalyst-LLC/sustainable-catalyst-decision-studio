#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v2.7.0."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "wordpress-plugin" / "sustainable-catalyst-decision-studio"
VERSION = "2.7.0"
BUILD = "scds-v2.7.0-site-intelligence-context-integration"
SOURCE = "release-v2.7.0"
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
ANALYSIS_HANDOFF = "scds-analysis-handoff/1.0"
COMPUTATION_HANDOFF = "scds-computation-handoff/1.0"
HANDOFF_RECEIPT = "scds-handoff-receipt/1.0"
ANALYSIS_REQUEST = "scds-analysis-request/1.0"
SITE_CONTEXT = "scds-site-intelligence-context-bundle/1.0"
SITE_SNAPSHOT = "scds-site-intelligence-signal-snapshot/1.0"
SITE_RECEIPT = "scds-site-intelligence-context-receipt/1.0"
PRODUCT_IDS = ["knowledge-library", "research-librarian", "site-intelligence", "workbench", "research-lab", "platform-core", "decision-studio"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


main = (ROOT / "backend/app/main.py").read_text()
native = (ROOT / "backend/app/native_handoffs.py").read_text()
site_context = (ROOT / "backend/app/site_intelligence_context.py").read_text()
scenario = (ROOT / "backend/app/scenario_stress.py").read_text()
uncertainty = (ROOT / "backend/app/uncertainty_confidence.py").read_text()
tradeoff = (ROOT / "backend/app/tradeoff_matrix.py").read_text()
evidence = (ROOT / "backend/app/evidence_bundle.py").read_text()
obj_model = (ROOT / "backend/app/decision_object.py").read_text()
energy_model = (ROOT / "backend/app/energy_runtime_consumer.py").read_text()
energy_test = (ROOT / "backend/tests/test_energy_runtime_consumer.py").read_text()
energy_doc = (ROOT / "ENERGY_RUNTIME_CONSUMER_2.3.0.md").read_text()
backend_tests = (ROOT / "backend/tests/test_backend.py").read_text()
php = (PLUGIN / "sustainable-catalyst-decision-studio.php").read_text()
js = (PLUGIN / "assets/js/scds-decision-studio.js").read_text()
docker = (ROOT / "backend/Dockerfile").read_text()
compose = (ROOT / "compose.yml").read_text()
render = (ROOT / "backend/render.yaml").read_text()
readme = (ROOT / "README.md").read_text()
changelog = (ROOT / "CHANGELOG.md").read_text()
doc = (ROOT / "docs/V270_SITE_INTELLIGENCE_CONTEXT_INTEGRATION.md").read_text()
plugin_readme = (PLUGIN / "readme.txt").read_text()

# Release identity.
require(f'APP_VERSION = "{VERSION}"' in main, "backend version")
for text in [main, php, docker, compose, render]:
    require(BUILD in text, "build fingerprint parity")
    require(SOURCE in text, "source commit parity")
require(" * Version: 2.7.0" in php and "const VERSION = '2.7.0';" in php, "plugin version")
require("Stable tag: 2.7.0" in plugin_readme, "stable tag")

# Schema lineage, including v2.6 native exchange.
all_schemas = [
    PACKET, OBJECT, CONTEXT, EVIDENCE, SOURCE_BUNDLE, COVERAGE,
    CRITERIA, ALTERNATIVES, MATRIX, DIAGNOSTICS,
    UNCERTAINTY, SENSITIVITY, CONFIDENCE,
    SCENARIO_SET, SCENARIO_COMPARISON, STRESS_SUITE,
    ANALYSIS_HANDOFF, COMPUTATION_HANDOFF, HANDOFF_RECEIPT, ANALYSIS_REQUEST,
    SITE_CONTEXT, SITE_SNAPSHOT, SITE_RECEIPT,
]
combined = main + php + native + site_context + scenario + uncertainty + tradeoff + evidence + obj_model + doc
for schema in all_schemas:
    require(schema in combined, f"schema parity/preservation {schema}")

# Native route parity.
routes = [
    "/native-handoffs/contracts",
    "/native-handoffs/template",
    "/native-handoffs/receive",
    "/native-handoffs/request",
    "/native-handoffs/return",
    "/decision-object/native-handoff",
    "/decision-packet/native-handoff",
]
for route in routes:
    require(route in main and route in php, f"route parity {route}")

site_routes = [
    "/site-intelligence-context/contracts", "/site-intelligence-context/template",
    "/site-intelligence-context/build", "/site-intelligence-context/validate",
    "/decision-object/site-intelligence-context", "/decision-packet/site-intelligence-context",
]
for route in site_routes:
    require(route in main and route in php, f"site context route parity {route}")

# Preserve v2.5 routes rather than replacing them.
for route in [
    "/scenario-set/template", "/scenario-set/build",
    "/scenario-analysis/template", "/scenario-analysis/compare",
    "/stress-test-suite/template", "/stress-test-suite/run",
    "/decision-object/scenario-stress", "/decision-packet/scenario-stress",
]:
    require(route in main and route in php, f"v2.5 route preserved {route}")

# WordPress UI and browser bindings.
for marker in [
    "Lab + Workbench Handoffs",
    "data-scds-v260-product",
    "data-scds-v260-source-version",
    "data-scds-v260-artifact-json",
    "data-scds-v260-request-json",
    "data-scds-v260-receive",
    "data-scds-v260-request",
    "data-scds-v260-return",
    "data-scds-v260-download",
    "Execution boundary:",
]:
    require(marker in php, f"WordPress UI {marker}")
for marker in [
    "nativeHandoffInputs", "nativeHandoffHtml", "runNativeHandoff", "downloadNativeHandoff",
    "restNativeHandoffContractsUrl", "restNativeHandoffTemplateUrl", "restNativeHandoffReceiveUrl",
    "restNativeHandoffRequestUrl", "restNativeHandoffReturnUrl",
    "restDecisionObjectNativeHandoffUrl", "restDecisionPacketNativeHandoffUrl",
]:
    require(marker in js + php, f"JS/WordPress binding {marker}")
for marker in [
    "Site Intelligence Context", "data-scds-v270-source-version", "data-scds-v270-geography",
    "data-scds-v270-signals-json", "data-scds-v270-build", "data-scds-v270-validate",
    "data-scds-v270-attach", "data-scds-v270-download", "Interpretation boundary:",
]:
    require(marker in php, f"Site context WordPress UI {marker}")
for marker in [
    "siteContextInputs", "siteContextHtml", "runSiteContext", "downloadSiteContext",
    "restSiteContextContractsUrl", "restSiteContextTemplateUrl", "restSiteContextBuildUrl",
    "restSiteContextValidateUrl", "restDecisionObjectSiteContextUrl", "restDecisionPacketSiteContextUrl",
]:
    require(marker in js + php, f"Site context JS/WordPress binding {marker}")

# Root/plugin release metadata must agree.
manifest = load(ROOT / "data/decision_studio_release_manifest_v2.7.0.json")
pmanifest = load(PLUGIN / "data/release_manifest_v2.7.0.json")
integrations = load(ROOT / "data/decision_studio_integrations_v2.7.0.json")
pintegrations = load(PLUGIN / "data/decision_studio_integrations_v2.7.0.json")
require(manifest == pmanifest, "manifest parity")
require(integrations == pintegrations, "integration parity")
require(manifest["release"] == VERSION, "manifest version")
require(manifest["build_fingerprint"] == BUILD and manifest["source_commit"] == SOURCE, "manifest build/source")

schemas = manifest["schemas"]
expected_schema_map = {
    "decision_packet": PACKET,
    "decision_object": OBJECT,
    "platform_context": CONTEXT,
    "evidence_bundle": EVIDENCE,
    "source_bundle": SOURCE_BUNDLE,
    "evidence_coverage": COVERAGE,
    "criteria_set": CRITERIA,
    "alternatives_set": ALTERNATIVES,
    "tradeoff_matrix": MATRIX,
    "tradeoff_diagnostics": DIAGNOSTICS,
    "uncertainty_register": UNCERTAINTY,
    "sensitivity_analysis": SENSITIVITY,
    "confidence_assessment": CONFIDENCE,
    "scenario_set": SCENARIO_SET,
    "scenario_comparison": SCENARIO_COMPARISON,
    "stress_test_suite": STRESS_SUITE,
    "analysis_handoff": ANALYSIS_HANDOFF,
    "computation_handoff": COMPUTATION_HANDOFF,
    "handoff_receipt": HANDOFF_RECEIPT,
    "analysis_request": ANALYSIS_REQUEST,
    "site_intelligence_context_bundle": SITE_CONTEXT,
    "site_intelligence_signal_snapshot": SITE_SNAPSHOT,
    "site_intelligence_context_receipt": SITE_RECEIPT,
}
for key, value in expected_schema_map.items():
    require(schemas.get(key) == value, f"manifest schema {key}")

# v2.6 contracts/samples match the WordPress copy exactly.
for stem in [
    "analysis_handoff_contract", "analysis_handoff_sample",
    "computation_handoff_contract", "computation_handoff_sample",
    "handoff_receipt_contract", "handoff_receipt_sample",
    "analysis_request_contract", "analysis_request_sample",
]:
    a = load(ROOT / f"data/{stem}_v2.6.0.json")
    b = load(PLUGIN / f"data/{stem}_v2.6.0.json")
    require(a == b, f"{stem} parity")

analysis_sample = load(ROOT / "data/analysis_handoff_sample_v2.6.0.json")
computation_sample = load(ROOT / "data/computation_handoff_sample_v2.6.0.json")
receipt_sample = load(ROOT / "data/handoff_receipt_sample_v2.6.0.json")
request_sample = load(ROOT / "data/analysis_request_sample_v2.6.0.json")
require(analysis_sample["schema"] == ANALYSIS_HANDOFF and analysis_sample["source"]["product"] == "research-lab", "analysis handoff sample")
require(computation_sample["schema"] == COMPUTATION_HANDOFF and computation_sample["source"]["product"] == "workbench", "computation handoff sample")
require(len(analysis_sample["artifact"]["fingerprint"]) == 64 and len(computation_sample["artifact"]["fingerprint"]) == 64, "artifact fingerprints")
require(receipt_sample["schema"] == HANDOFF_RECEIPT and receipt_sample["accepted"] is True, "handoff receipt sample")
require(receipt_sample["execution"]["performed"] is False, "receipt does not execute source work")
require(request_sample["schema"] == ANALYSIS_REQUEST and request_sample["execution"]["performed_by_decision_studio"] is False, "analysis request execution boundary")
require(len(request_sample["request_fingerprint"]) == 64, "analysis request fingerprint")

for stem in [
    "site_intelligence_context_bundle_contract", "site_intelligence_context_bundle_sample",
    "site_intelligence_signal_snapshot_contract", "site_intelligence_signal_snapshot_sample",
    "site_intelligence_context_receipt_contract", "site_intelligence_context_receipt_sample",
]:
    a = load(ROOT / f"data/{stem}_v2.7.0.json")
    b = load(PLUGIN / f"data/{stem}_v2.7.0.json")
    require(a == b, f"{stem} parity")
site_bundle_sample = load(ROOT / "data/site_intelligence_context_bundle_sample_v2.7.0.json")
site_snapshot_sample = load(ROOT / "data/site_intelligence_signal_snapshot_sample_v2.7.0.json")
site_receipt_sample = load(ROOT / "data/site_intelligence_context_receipt_sample_v2.7.0.json")
require(site_bundle_sample["schema"] == SITE_CONTEXT and len(site_bundle_sample["bundle_fingerprint"]) == 64, "site context bundle sample")
require(site_snapshot_sample["schema"] == SITE_SNAPSHOT and len(site_snapshot_sample["signal_fingerprint"]) == 64, "site snapshot sample")
require(site_receipt_sample["schema"] == SITE_RECEIPT and site_receipt_sample["truth_verified"] is False, "site context receipt sample")

# Human-control and source-ownership boundaries.
compat = manifest["compatibility"]
for flag in [
    "lab_native_handoffs", "workbench_native_handoffs", "bidirectional_analysis_requests",
    "source_artifact_payload_preserved", "deterministic_handoff_fingerprints",
    "v2_5_0_scenario_stress_preserved", "v2_4_0_uncertainty_confidence_preserved",
    "v2_3_1_tradeoff_matrix_preserved", "v2_3_0_energy_runtime_consumer_preserved",
    "v2_6_0_native_handoffs_preserved", "site_intelligence_context_bundles",
    "site_intelligence_source_identity_preserved", "site_intelligence_geography_preserved",
    "site_intelligence_observation_time_visible", "site_intelligence_freshness_visible",
    "site_intelligence_methodology_limitations_visible", "explicit_scenario_context_links",
]:
    require(compat.get(flag) is True, f"compatibility true: {flag}")
for flag in [
    "handoff_receipt_implies_validation", "decision_studio_executes_external_analysis",
    "automatic_winner_selection", "automatic_recommendation", "automatic_truth_verification",
    "confidence_is_probability_of_correctness", "scenario_likelihood_inference", "stress_test_pass_implies_approval",
    "site_intelligence_context_implies_causality", "site_intelligence_context_implies_recommendation",
    "site_intelligence_context_receipt_implies_truth_verification", "decision_studio_rewrites_site_intelligence_observations",
]:
    require(compat.get(flag) is False, f"compatibility false: {flag}")
require(compat.get("energy_runtime_consumer_version") == "2.3.0", "Energy consumer component version")
require("Decision Studio does not execute Lab experiments" in native and "Workbench computations" in native, "source execution boundary")
require("artifact fingerprint does not match payload" in native, "tamper detection")
require("performed_by_decision_studio" in native, "request execution boundary")
require("does not infer causality" in site_context and "recommendation" in site_context, "site context interpretation boundary")
require("signal fingerprint does not match raw payload" in site_context, "site signal tamper detection")

# Backend regression coverage for the new exchange lifecycle.
for test_name in [
    "test_v260_contracts_and_templates_exposed",
    "test_v260_lab_handoff_preserves_exact_artifact_payload_and_fingerprint",
    "test_v260_workbench_handoff_is_computation_contract",
    "test_v260_handoff_rejects_tampered_payload_fingerprint",
    "test_v260_decision_studio_can_request_lab_analysis_without_executing_it",
    "test_v260_decision_studio_can_request_workbench_computation",
    "test_v260_lab_return_attaches_to_decision_object_with_lineage",
    "test_v260_workbench_return_attaches_to_decision_packet_without_breaking_schema",
    "test_v260_return_can_link_back_to_analysis_request",
    "test_v260_release_declares_native_handoffs_and_preserves_boundaries",
]:
    require(test_name in backend_tests, f"backend regression test {test_name}")
for test_name in [
    "test_v270_templates_expose_site_intelligence_context_contracts",
    "test_v270_context_bundle_preserves_source_geography_time_freshness_and_raw_payload",
    "test_v270_context_diagnostics_surface_missing_metadata_without_inventing_it",
    "test_v270_explicit_scenario_links_do_not_change_scores_or_infer_likelihood",
    "test_v270_context_bundle_rejects_tampered_signal_payload",
    "test_v270_decision_object_attachment_preserves_context_and_receipt_boundaries",
    "test_v270_decision_packet_projection_keeps_live_snapshots_and_decision_object",
    "test_v270_release_declares_site_intelligence_context_and_human_control_boundaries",
]:
    require(test_name in backend_tests, f"v2.7 backend regression test {test_name}")

# Energy v2.3.0 remains a distinct preserved component.
for marker in ["CONSUMER_VERSION = '2.3.0'", "/v1/energy-runtime", "sc-energy-runtime-decision-studio-handoff/1.0"]:
    require(marker in energy_model + energy_doc + main, f"Energy runtime preservation {marker}")
require("test_consume_builds_ephemeral_receipt" in energy_test, "Energy runtime regression test preserved")
require("energy_runtime_consumer_router" in main, "Energy runtime router registered")
require("'energy_systems_runtime_consumer'=>true" in php and "'energy_runtime_consumer_version'=>'2.3.0'" in php, "WordPress Energy preservation")
require([x["id"] for x in integrations["platform_context"]] == PRODUCT_IDS, "platform context preserved")

# Runtime/deployment identity.
require("python:3.12-slim" in docker and "8089" in docker and "2.7.0" in docker, "Docker runtime identity")
require("sustainable-catalyst-decision-studio:2.7.0" in compose and "sc-decision-studio" in compose and "sc-internal" in compose, "Contabo compose identity")

# Historical artifacts remain in the repository.
for path in [
    "data/decision_studio_release_manifest_v2.6.0.json", "data/analysis_handoff_contract_v2.6.0.json", "data/computation_handoff_contract_v2.6.0.json",
    "data/decision_studio_release_manifest_v2.5.0.json", "data/scenario_set_contract_v2.5.0.json", "data/stress_test_suite_contract_v2.5.0.json",
    "data/decision_studio_release_manifest_v2.4.0.json", "data/confidence_assessment_contract_v2.4.0.json",
    "data/decision_studio_release_manifest_v2.3.1.json", "data/tradeoff_matrix_contract_v2.3.1.json",
    "data/decision_studio_release_manifest_v2.2.0.json", "data/evidence_bundle_contract_v2.2.0.json", "data/source_bundle_contract_v2.2.0.json",
    "data/decision_studio_release_manifest_v2.1.0.json", "data/decision_object_contract_v2.1.0.json", "data/platform_context_contract_v2.1.0.json",
    "data/decision_studio_release_manifest_v2.0.1.json",
]:
    require((ROOT / path).exists(), f"preserved {path}")

# v2.5 scenario/stress and earlier capabilities remain executable in source.
require("ordering_changed_vs_baseline" in scenario, "scenario ordering diagnostics preserved")
require("failure_codes" in scenario, "stress failure diagnostics preserved")
require("automatic_winner_selection" in main + php and "automatic_recommendation" in main + php, "human-control markers")
require("Scenario Comparison & Stress Testing" in changelog + plugin_readme, "v2.5 documentation preserved")
require("Lab + Workbench Native Handoffs" in readme + changelog + plugin_readme, "v2.6 documentation preserved")
require("Site Intelligence Context Integration" in readme + changelog + doc + plugin_readme, "v2.7 documentation")

# Every JSON file in the package must parse.
json_files = [p for p in ROOT.rglob("*.json") if ".git" not in p.parts]
for path in json_files:
    load(path)

print(
    f"Decision Studio v{VERSION} release-integrity checks passed. "
    f"Validated {len(json_files)} JSON files, {len(PRODUCT_IDS)} platform roles, "
    "Site Intelligence context v1.0 contracts, Lab/Workbench v2.6 preservation, v2.5 Scenario/Stress preservation, and Energy v2.3.0 preservation."
)
