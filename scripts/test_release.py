#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v1.10.0."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.10.0"
BUILD = "scds-v1.10.0-advanced-scenario-sensitivity"
PACKET_SCHEMA = "scds-decision-packet/1.3"
SCENARIO_SCHEMA = "scds-scenario-studio/1.0"
ARTIFACT_SCHEMA = "scds-platform-artifact/1.0"
EVIDENCE_SCHEMA = "scds-evidence-record/1.0"
GOVERNANCE_SCHEMA = "scds-decision-governance/1.0"
REVIEW_EVENT_SCHEMA = "scds-review-event/1.0"
PRODUCTS = ("knowledge-library", "research-librarian", "site-intelligence", "workbench", "research-lab", "platform-core")
STATES = ("draft", "evidence_gathering", "analysis", "review", "revision_required", "approved", "rejected", "deferred", "implemented", "retired")
ROUTES = (
    "/scenario-studio/template", "/scenario-studio/analyze", "/scenario-studio/sensitivity",
    "/scenario-studio/threshold", "/decision-packet/scenario-studio",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")
    print(f"PASS: {message}")


backend = (ROOT / "backend/app/main.py").read_text()
tests = (ROOT / "backend/tests/test_backend.py").read_text()
plugin_path = ROOT / "wordpress-plugin/sustainable-catalyst-decision-studio/sustainable-catalyst-decision-studio.php"
plugin = plugin_path.read_text()
plugin_js = (plugin_path.parent / "assets/js/scds-decision-studio.js").read_text()
plugin_css = (plugin_path.parent / "assets/css/scds-decision-studio.css").read_text()
plugin_readme = (plugin_path.parent / "readme.txt").read_text()
render = (ROOT / "backend/render.yaml").read_text()
manifest = json.loads((ROOT / "data/decision_studio_release_manifest_v1.10.0.json").read_text())
plugin_manifest = json.loads((plugin_path.parent / "data/release_manifest_v1.10.0.json").read_text())
governance = json.loads((ROOT / "data/governance_state_catalog_v1.9.0.json").read_text())
plugin_governance = json.loads((plugin_path.parent / "data/governance_state_catalog_v1.9.0.json").read_text())
contracts = json.loads((ROOT / "data/platform_handoff_contracts_v1.8.0.json").read_text())
samples = json.loads((ROOT / "data/sample_platform_artifacts_v1.8.0.json").read_text())
scenario_contract = json.loads((ROOT / "data/scenario_studio_contract_v1.10.0.json").read_text())
plugin_scenario_contract = json.loads((plugin_path.parent / "data/scenario_studio_contract_v1.10.0.json").read_text())
scenario_sample = json.loads((ROOT / "data/scenario_studio_sample_v1.10.0.json").read_text())
plugin_scenario_sample = json.loads((plugin_path.parent / "data/scenario_studio_sample_v1.10.0.json").read_text())
integrations = json.loads((ROOT / "data/decision_studio_integrations_v1.10.0.json").read_text())

require(f'APP_VERSION = "{VERSION}"' in backend, "backend version marker")
require(f" * Version: {VERSION}" in plugin, "WordPress plugin header version")
require(f"const VERSION = '{VERSION}';" in plugin, "WordPress runtime version")
require(f"Stable tag: {VERSION}" in plugin_readme, "WordPress stable tag")
require(BUILD in backend and BUILD in plugin and BUILD in render, "build fingerprint parity")
require("release-v1.10.0" in backend and "release-v1.10.0" in plugin and "release-v1.10.0" in render, "source release identity parity")
require(manifest == plugin_manifest, "repository and plugin manifests match")
require(manifest["release"] == VERSION, "manifest release version")
require(manifest["wordpress"]["database_version"] == "1.4.0", "WordPress scenario persistence migration")
require(manifest["schemas"]["decision_packet"] == PACKET_SCHEMA, "Decision Packet schema")
require(manifest["schemas"]["scenario_studio"] == SCENARIO_SCHEMA, "Scenario Studio schema")
require(manifest["schemas"]["decision_governance"] == GOVERNANCE_SCHEMA, "governance schema retained")
require(manifest["compatibility"]["packet_schema_breaking_changes"] is False, "additive packet compatibility")
require(manifest["compatibility"]["legacy_artifact_adapters_preserved"] is True, "legacy adapters preserved")
require(manifest["compatibility"]["v1_9_governance_preserved"] is True, "v1.9 governance preserved")
require(set(manifest["platform_products"]) == set(PRODUCTS), "six current platform products retained")
require(manifest["advanced_scenario_studio"]["alternative_limit"] == 100, "100-alternative safety cap")
require(manifest["advanced_scenario_studio"]["probabilistic_simulation_boundary"] == "Workbench", "Workbench computation boundary")
require(manifest["advanced_scenario_studio"]["forecast_claims_allowed"] is False, "scenario results not represented as forecasts")

require(governance == plugin_governance, "repository and plugin governance catalogs match")
require(tuple(item["id"] for item in governance["states"]) == STATES, "ten governance states retained")
require(governance["history"]["hash_algorithm"] == "SHA-256", "SHA-256 review history retained")
require(len(contracts["contracts"]) == 6 and len(samples) == 6, "v1.8 platform contracts and fixtures retained")
require(scenario_contract == plugin_scenario_contract, "repository and plugin scenario contracts match")
require(scenario_sample == plugin_scenario_sample, "repository and plugin scenario samples match")
require(scenario_contract["schema"] == SCENARIO_SCHEMA, "scenario contract schema")
require(scenario_contract["alternative_limit"] == 100, "scenario contract alternative limit")
require(len(scenario_contract["criteria"]) >= 8, "scenario contract default criteria")
require(scenario_sample["response"]["scenario_studio"]["alternative_count"] == 3, "scenario fixture has three alternatives")
require(integrations["scenario_studio_schema"] == SCENARIO_SCHEMA, "integration manifest scenario schema")
require(integrations["decision_packet_schema"] == PACKET_SCHEMA, "integration manifest packet schema")

for schema in (PACKET_SCHEMA, SCENARIO_SCHEMA, ARTIFACT_SCHEMA, EVIDENCE_SCHEMA, GOVERNANCE_SCHEMA, REVIEW_EVENT_SCHEMA):
    require(schema in backend, f"backend schema marker: {schema}")
    require(schema in plugin or schema in plugin_js, f"WordPress/browser schema marker: {schema}")

for route in ROUTES:
    require(route in backend, f"backend route: {route}")
    require(route in plugin, f"WordPress route: {route}")

for token in (
    "alternatives", "criteria", "parameterRanges", "sensitivityParameters", "thresholdTarget",
    "timeHorizons", "gridPoints", "includeMultiVariable",
):
    require(token in backend, f"backend scenario request field: {token}")

for token in (
    "weighted_ranking", "unweighted_ranking", "one_way_sensitivity", "multi_variable_sensitivity",
    "threshold_analysis", "uncertainty_envelopes", "time_horizon_comparison",
    "stakeholder_distribution", "dominance_analysis", "reversibility_option_value",
):
    require(token in backend and token in plugin, f"backend/WordPress scenario output parity: {token}")

require("scenario_studio_json LONGTEXT" in plugin, "WordPress scenario persistence column")
require("'scenario_studio_json'=>wp_json_encode" in plugin, "WordPress scenario save persistence")
require("data-scds-scenario-studio-run" in plugin and "runScenarioStudio" in plugin_js, "Scenario Studio UI behavior")
require("data-scds-scenario-studio-sensitivity" in plugin, "sensitivity action control")
require("data-scds-scenario-studio-threshold" in plugin, "break-even action control")
require("scenarioStudioPayload" in plugin_js and "scenarioStudioHtml" in plugin_js, "browser scenario payload and rendering")
require("scenario_studio_json" in backend and "scenario_studio_json" in plugin, "advanced scenario export")
require("probabilistic simulation" in backend and "probabilistic simulation" in plugin, "Workbench escalation boundary")
require("not forecasts or guarantees" in backend and "not forecasts or guarantees" in plugin, "scenario interpretation warning")
require("governance_export_blocked" in backend and "scds_governance_export_blocked" in plugin, "governance-aware export blocking retained")
require("previous_hash" in backend and "event_hash" in backend and "previous_hash" in plugin and "event_hash" in plugin, "tamper-evident review history retained")

for product in PRODUCTS:
    require(product in backend and product in plugin and product in plugin_js, f"typed platform product retained: {product}")
for shortcode in ("sc_decision_studio", "sustainable_catalyst_platform", "sustainable_catalyst_platform_cta"):
    require(f"add_shortcode('{shortcode}'" in plugin, f"shortcode preserved: {shortcode}")
require("mode=\"scenario\"" in plugin_readme, "scenario shortcode documented")
require("mode=\"governance\"" in plugin_readme, "governance shortcode documented")
require("rootDir: backend" in render and "PYTHON_VERSION" in render and "3.12.11" in render, "Render deployment remains Python 3.12")
require((ROOT / "docs/V1100_ADVANCED_SCENARIO_SENSITIVITY_STUDIO.md").exists(), "v1.10.0 architecture documentation")
require((ROOT / "terminal/V1100_ADVANCED_SCENARIO_SENSITIVITY_STUDIO_COMMANDS.txt").exists(), "v1.10.0 terminal guide")
require("test_scenario_studio_supports_custom_alternatives_and_weighted_unweighted_rankings" in tests, "custom alternatives regression test")
require("test_scenario_studio_one_way_sensitivity_and_tornado_ranking" in tests, "one-way sensitivity regression test")
require("test_scenario_studio_threshold_break_even_search" in tests, "break-even regression test")
require("test_scenario_studio_stakeholder_distribution_and_option_value" in tests, "stakeholder and option-value regression test")
require("test_scenario_studio_is_saved_and_exported" in tests, "scenario persistence/export regression test")
require("v1.10.0 — Advanced Scenario and Sensitivity Studio" in (ROOT / "docs/ROADMAP.md").read_text(), "canonical roadmap updated")
require("v1.11.0 — Collaborative Decision Rooms" in (ROOT / "docs/ROADMAP.md").read_text(), "next roadmap release retained")
print("Release integrity checks passed.")
