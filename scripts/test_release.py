#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v1.14.0."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "wordpress-plugin/sustainable-catalyst-decision-studio"
PLUGIN_PHP = PLUGIN_ROOT / "sustainable-catalyst-decision-studio.php"
VERSION = "1.14.0"
BUILD = "scds-v1.14.0-outcomes-monitoring-reassessment"
SOURCE = "release-v1.14.0"
PACKET_SCHEMA = "scds-decision-packet/1.7"
OUTCOME_SCHEMA = "scds-outcome-monitoring/1.0"
REASSESSMENT_SCHEMA = "scds-reassessment-event/1.0"
REGISTRY_SCHEMA = "scds-decision-registry-entry/1.0"
PRODUCTS = {
    "knowledge-library", "research-librarian", "site-intelligence",
    "workbench", "research-lab", "platform-core",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")
    print(f"PASS: {message}")


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


backend = (ROOT / "backend/app/main.py").read_text(encoding="utf-8")
outcomes = (ROOT / "backend/app/outcome_monitoring.py").read_text(encoding="utf-8")
tests = (ROOT / "backend/tests/test_backend.py").read_text(encoding="utf-8")
plugin = PLUGIN_PHP.read_text(encoding="utf-8")
js = (PLUGIN_ROOT / "assets/js/scds-decision-studio.js").read_text(encoding="utf-8")
css = (PLUGIN_ROOT / "assets/css/scds-decision-studio.css").read_text(encoding="utf-8")
plugin_readme = (PLUGIN_ROOT / "readme.txt").read_text(encoding="utf-8")
render = (ROOT / "backend/render.yaml").read_text(encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")
roadmap = (ROOT / "docs/ROADMAP.md").read_text(encoding="utf-8")
changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
doc = (ROOT / "docs/V1140_OUTCOMES_MONITORING_REASSESSMENT.md").read_text(encoding="utf-8")
terminal = (ROOT / "terminal/V1140_OUTCOMES_MONITORING_REASSESSMENT_COMMANDS.txt").read_text(encoding="utf-8")
manifest = load_json(ROOT / "data/decision_studio_release_manifest_v1.14.0.json")
plugin_manifest = load_json(PLUGIN_ROOT / "data/release_manifest_v1.14.0.json")
integrations = load_json(ROOT / "data/decision_studio_integrations_v1.14.0.json")
contract = load_json(ROOT / "data/outcome_monitoring_contract_v1.14.0.json")
plugin_contract = load_json(PLUGIN_ROOT / "data/outcome_monitoring_contract_v1.14.0.json")
sample = load_json(ROOT / "data/outcome_monitoring_sample_v1.14.0.json")
plugin_sample = load_json(PLUGIN_ROOT / "data/outcome_monitoring_sample_v1.14.0.json")

# Identity and deployment.
require(f'APP_VERSION = "{VERSION}"' in backend, "backend version marker")
require(f" * Version: {VERSION}" in plugin, "WordPress plugin header version")
require(f"const VERSION = '{VERSION}';" in plugin, "WordPress runtime version")
require(f"Stable tag: {VERSION}" in plugin_readme, "WordPress stable tag")
require(BUILD in backend and BUILD in plugin and BUILD in render, "build fingerprint parity")
require(SOURCE in backend and SOURCE in plugin and SOURCE in render, "source release identity parity")
require("rootDir: backend" in render and "3.12.11" in render, "Render root and Python 3.12 runtime")
require("healthCheckPath: /health" in render, "Render health check")
require('VERSION="1.14.0"' in (ROOT / "scripts/build_release.sh").read_text(), "release packaging version")

# Manifest and additive schema identity.
require(manifest == plugin_manifest, "repository and plugin release manifests match")
require(manifest["release"] == VERSION, "release manifest version")
require(manifest["wordpress"]["database_version"] == "1.8.0", "WordPress database migration 1.8.0")
require(manifest["schemas"]["decision_packet"] == PACKET_SCHEMA, "Decision Packet schema 1.7")
require(manifest["schemas"]["outcome_monitoring"] == OUTCOME_SCHEMA, "outcome monitoring schema")
require(manifest["schemas"]["reassessment_event"] == REASSESSMENT_SCHEMA, "reassessment event schema")
require(manifest["schemas"]["decision_registry_entry"] == REGISTRY_SCHEMA, "Decision Registry schema")
require(manifest["compatibility"]["packet_schema_breaking_changes"] is False, "additive packet compatibility")
require(manifest["compatibility"]["v1_13_publication_studio_preserved"] is True, "v1.13 publication preserved")
require(manifest["compatibility"]["v1_12_decision_packs_preserved"] is True, "v1.12 Decision Packs preserved")
require(manifest["compatibility"]["v1_11_collaboration_preserved"] is True, "v1.11 collaboration preserved")
require(manifest["compatibility"]["v1_10_scenario_studio_preserved"] is True, "v1.10 scenario studio preserved")
require(manifest["compatibility"]["v1_9_governance_preserved"] is True, "v1.9 governance preserved")
require(manifest["compatibility"]["legacy_artifact_adapters_preserved"] is True, "legacy adapters preserved")
require(set(manifest["platform_products"]) == PRODUCTS, "six current platform products retained")
require(manifest["outcomes_monitoring"]["human_reassessment_required"] is True, "human reassessment boundary")
require(manifest["outcomes_monitoring"]["ai_approval_allowed"] is False, "AI approval prohibited")

# Outcome contracts and sample.
require(contract == plugin_contract, "repository and plugin outcome contracts match")
require(sample == plugin_sample, "repository and plugin outcome samples match")
require(contract["properties"]["schema"]["const"] == OUTCOME_SCHEMA, "outcome contract schema identity")
require(contract["properties"]["reassessment_history"]["items"]["properties"]["schema"]["const"] == REASSESSMENT_SCHEMA, "reassessment contract identity")
require(contract["properties"]["decision_registry_entry"]["properties"]["schema"]["const"] == REGISTRY_SCHEMA, "registry contract identity")
require(sample["schema"] == OUTCOME_SCHEMA, "sample outcome schema")
require(sample["status"] == "reassessment_required", "sample detects reassessment requirement")
require(sample["summary"]["triggered_reassessments"] >= 1, "sample trigger evaluation")
require(sample["content_hash"].startswith("sha256:") and len(sample["content_hash"]) == 71, "sample content hash format")
require(sample["decision_registry_entry"]["registry_hash"].startswith("sha256:"), "sample Decision Registry hash")
require(integrations["decision_packet_schema"] == PACKET_SCHEMA, "integration manifest packet schema")
require(integrations["outcome_monitoring_schema"] == OUTCOME_SCHEMA, "integration manifest outcome schema")
require(integrations["reassessment_event_schema"] == REASSESSMENT_SCHEMA, "integration manifest reassessment schema")
require(integrations["decision_registry_schema"] == REGISTRY_SCHEMA, "integration manifest registry schema")
require(integrations["outcomes_monitoring_reassessment"]["human_authorization_required"] is True, "integration human authorization boundary")

# Backend engine and API.
for marker in [
    'OUTCOME_MONITORING_SCHEMA = "scds-outcome-monitoring/1.0"',
    'REASSESSMENT_EVENT_SCHEMA = "scds-reassessment-event/1.0"',
    'DECISION_REGISTRY_SCHEMA = "scds-decision-registry-entry/1.0"',
    'class OutcomeMonitoringRequest(BaseModel)', 'def outcome_monitoring_template()',
    'def generate_outcome_monitoring(', 'def _evaluate_indicator(', 'def _evaluate_trigger(',
    '@app.get("/outcomes/template")', '@app.post("/outcomes/evaluate")',
    '@app.post("/outcomes/record-observation")', '@app.post("/outcomes/reassess")',
    '@app.post("/outcomes/amend")', '@app.post("/outcomes/retire")',
    '@app.post("/decision-packet/outcomes")',
    '"outcome_monitoring": outcome_monitoring_template()', '"decision_registry_entry": {}',
    '"reassessment_history": []', '"implementation_amendments": []',
    '"outcome_monitoring_json"', '"decision_registry_json"', '"reassessment_history_json"',
]:
    require(marker in backend or marker in outcomes, f"backend marker: {marker}")
require('if not req.actor.strip()' in outcomes, "named-human lifecycle authorization")
require('"human_authorized": True' in outcomes, "human-authorized amendment/retirement records")
require('"human_authorization_required": True' in outcomes, "human reassessment requirement")
require('"source_url"' in outcomes and '"methodology"' in outcomes and '"confidence"' in outcomes, "source-aware observations")
require('"previous_event_hash"' in outcomes and '"event_hash"' in outcomes, "tamper-evident monitoring events")
require('monitoring["status"] = "reassessment_required"' in outcomes, "reassessment-required status")

# Backend regression coverage.
for phrase in [
    "test_outcomes_template_contracts",
    "test_outcomes_evaluation_detects_reassessment_need",
    "test_outcomes_indicator_direction_and_tolerance",
    "test_record_observation_updates_indicator_and_hash_chain",
    "test_observation_requires_indicator_and_numeric_value",
    "test_reassessment_requires_named_human_actor",
    "test_reassessment_creates_human_owned_event",
    "test_amendment_and_retirement_require_human_authorization",
    "test_outcomes_update_packet_registry_and_exports",
    "test_outcomes_saved_and_exported",
]:
    require(phrase in tests, f"backend regression test: {phrase}")

# WordPress database, routes, fallback, UI, persistence, and exports.
for marker in [
    "const DB_VERSION = '1.8.0';",
    "const OUTCOME_MONITORING_SCHEMA = 'scds-outcome-monitoring/1.0';",
    "const REASSESSMENT_EVENT_SCHEMA = 'scds-reassessment-event/1.0';",
    "const DECISION_REGISTRY_SCHEMA = 'scds-decision-registry-entry/1.0';",
    "outcome_monitoring_json LONGTEXT",
    "render_panel_outcomes", "outcome_monitoring_template", "evaluate_outcomes_local",
    "rest_outcomes_template", "rest_outcomes_action",
    "'/outcomes/template'", "'/outcomes/evaluate'", "'/outcomes/record-observation'",
    "'/outcomes/reassess'", "'/outcomes/amend'", "'/outcomes/retire'", "'/decision-packet/outcomes'",
    "'outcome_monitoring_json'", "'decision_registry_json'", "'reassessment_history_json'",
    '[sc_decision_studio mode="outcomes"',
]:
    require(marker in plugin or marker in plugin_readme, f"WordPress marker: {marker}")
require("current_user_can('edit_posts')" in plugin, "authenticated reassessment/amendment/retirement routes")
require("array_is_list" not in plugin, "PHP 7.4-compatible array handling")
require(plugin.count("'outcome_monitoring_schema'=>self::OUTCOME_MONITORING_SCHEMA") >= 2, "WordPress outcome schema exposed")

# Browser workspace.
for marker in [
    "function outcomePayload(root,action)", "function localOutcomeEvaluate(payload)",
    "function outcomeOutputHtml(m)", "function runOutcomes(root,action)",
    "function downloadOutcomes(root)",
    "data-scds-outcomes-evaluate", "data-scds-outcomes-observe", "data-scds-outcomes-reassess",
    "data-scds-outcomes-amend", "data-scds-outcomes-retire", "data-scds-outcomes-download",
    "decision-studio-outcome-monitoring-v1.14.0.json", "outcome_monitoring:outcomeMonitoring",
    "scds_saved_decision_packets_v1_14_0",
]:
    require(marker in js or marker in plugin, f"browser marker: {marker}")
require("v1.13.0" not in js, "no stale v1.13 browser release filenames")
for marker in ["v1.14.0 Outcomes, Monitoring, and Reassessment", '[data-scds-panel="outcomes"] .scds-score-grid']:
    require(marker in css, f"outcome CSS marker: {marker}")

# Documentation and roadmap.
for text, label in [
    (readme, "repository README"), (plugin_readme, "plugin readme"),
    (roadmap, "roadmap"), (changelog, "changelog"), (doc, "outcomes documentation"),
    (terminal, "terminal commands"),
]:
    require(VERSION in text, f"{label} version")
require("v1.15.0 — Public API, Embeds, and Institutional Integration" in roadmap, "next roadmap release")
require("Site Intelligence" in doc and "human" in doc.lower() and "Decision Registry" in doc, "outcomes documentation coverage")
require('[sc_decision_studio mode="outcomes"' in plugin_readme and '[sc_decision_studio mode="outcomes"' in doc, "outcomes shortcode documentation")

print("Decision Studio v1.14.0 release-integrity checks passed.")
