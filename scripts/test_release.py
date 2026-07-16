#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v1.9.0."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.9.0"
BUILD = "scds-v1.9.0-decision-governance"
PACKET_SCHEMA = "scds-decision-packet/1.2"
ARTIFACT_SCHEMA = "scds-platform-artifact/1.0"
EVIDENCE_SCHEMA = "scds-evidence-record/1.0"
GOVERNANCE_SCHEMA = "scds-decision-governance/1.0"
REVIEW_EVENT_SCHEMA = "scds-review-event/1.0"
PRODUCTS = ("knowledge-library", "research-librarian", "site-intelligence", "workbench", "research-lab", "platform-core")
STATES = ("draft", "evidence_gathering", "analysis", "review", "revision_required", "approved", "rejected", "deferred", "implemented", "retired")

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
manifest = json.loads((ROOT / "data/decision_studio_release_manifest_v1.9.0.json").read_text())
plugin_manifest = json.loads((plugin_path.parent / "data/release_manifest_v1.9.0.json").read_text())
governance = json.loads((ROOT / "data/governance_state_catalog_v1.9.0.json").read_text())
plugin_governance = json.loads((plugin_path.parent / "data/governance_state_catalog_v1.9.0.json").read_text())
contracts = json.loads((ROOT / "data/platform_handoff_contracts_v1.8.0.json").read_text())
samples = json.loads((ROOT / "data/sample_platform_artifacts_v1.8.0.json").read_text())

require(f'APP_VERSION = "{VERSION}"' in backend, "backend version marker")
require(f" * Version: {VERSION}" in plugin, "WordPress plugin header version")
require(f"const VERSION = '{VERSION}';" in plugin, "WordPress runtime version")
require(f"Stable tag: {VERSION}" in plugin_readme, "WordPress stable tag")
require(BUILD in backend and BUILD in plugin and BUILD in render, "build fingerprint parity")
require(manifest == plugin_manifest, "repository and plugin manifests match")
require(manifest["release"] == VERSION, "manifest release version")
require(manifest["wordpress"]["database_version"] == "1.3.0", "WordPress governance database migration")
require(manifest["schemas"]["decision_packet"] == PACKET_SCHEMA, "Decision Packet schema")
require(manifest["schemas"]["decision_governance"] == GOVERNANCE_SCHEMA, "governance schema")
require(manifest["schemas"]["review_event"] == REVIEW_EVENT_SCHEMA, "review event schema")
require(manifest["compatibility"]["packet_schema_breaking_changes"] is False, "additive packet compatibility")
require(manifest["compatibility"]["legacy_artifact_adapters_preserved"] is True, "legacy adapters preserved")
require(set(manifest["platform_products"]) == set(PRODUCTS), "six current platform products retained")
require(governance == plugin_governance, "repository and plugin governance catalogs match")
require(tuple(item["id"] for item in governance["states"]) == STATES, "ten governance states in canonical order")
require(governance["history"]["hash_algorithm"] == "SHA-256", "SHA-256 immutable review history")
require(governance["export_policy"]["professional_reliance"] == "never automated", "no automated professional reliance")
require(len(contracts["contracts"]) == 6 and len(samples) == 6, "v1.8 platform contracts and fixtures retained")

for schema in (PACKET_SCHEMA, ARTIFACT_SCHEMA, EVIDENCE_SCHEMA, GOVERNANCE_SCHEMA, REVIEW_EVENT_SCHEMA):
    require(schema in backend, f"backend schema marker: {schema}")
    require(schema in plugin or schema in plugin_js, f"WordPress/browser schema marker: {schema}")
for state in STATES:
    require(state in backend and state in plugin, f"governance state: {state}")
for token in ("decisionOwner", "reviewers", "approvalConditions", "exceptions", "conflictDeclarations", "signoffs", "reviewHistory"):
    require(token in backend, f"backend governance request field: {token}")
for token in ("missing_decision_owner", "missing_reviewer_approval", "missing_owner_signoff", "missing_governance_signoff", "open_material_exception", "unmitigated_conflict", "invalid_transition"):
    require(token in backend and token in plugin and token in plugin_js, f"governance blocker parity: {token}")
for route in ("/governance/states", "/governance/template", "/governance/evaluate", "/governance/transition", "/decision-packet/governance", "/governance/history/verify"):
    require(route in backend, f"backend route: {route}")
    require(f"'{route}'" in plugin, f"WordPress route: {route}")
require("_append_review_event" in backend and "verify_review_history" in backend, "backend review history engine")
require("append_review_event" in plugin and "verify_review_history" in plugin, "WordPress review history engine")
require("previous_hash" in backend and "event_hash" in backend, "backend hash-chain fields")
require("previous_hash" in plugin and "event_hash" in plugin, "WordPress hash-chain fields")
require("governance_export_blocked" in backend and "scds_governance_export_blocked" in plugin, "governance-aware export blocking")
require("exportAudience" in backend and "exportAudience" in plugin and "exportAudience" in plugin_js, "export audience support")
require("status_code=409" in backend and "'status'=>409" in plugin, "blocked reviewed/public export status")
require("governance_json LONGTEXT" in plugin, "WordPress governance persistence column")
require("'governance_json'=>wp_json_encode" in plugin, "WordPress governance save persistence")
require("data-scds-panel=\"governance\"" in plugin, "Governance UI panel")
require("data-scds-governance-evaluate" in plugin and "runGovernance" in plugin_js, "Governance UI behavior")
require("browser_fallback_requires_server_verification" in plugin_js, "browser history integrity boundary")
require("professional_reliance_allowed" in backend and "professional_reliance_allowed" in plugin, "professional reliance remains disabled")
require("AI may flag gaps or contradictions" in backend and "AI may flag gaps or contradictions" in plugin, "AI approval boundary")

for product in PRODUCTS:
    require(product in backend and product in plugin and product in plugin_js, f"v1.8 platform product retained: {product}")
for shortcode in ("sc_decision_studio", "sustainable_catalyst_platform", "sustainable_catalyst_platform_cta"):
    require(f"add_shortcode('{shortcode}'" in plugin, f"shortcode preserved: {shortcode}")
require("mode=\"governance\"" in plugin_readme, "governance shortcode documented")
require("rootDir: backend" in render and "PYTHON_VERSION" in render and "3.12.11" in render, "Render deployment remains Python 3.12")
require((ROOT / "docs/V190_DECISION_GOVERNANCE_REVIEW_CENTER.md").exists(), "v1.9.0 architecture documentation")
require((ROOT / "terminal/V190_DECISION_GOVERNANCE_REVIEW_CENTER_COMMANDS.txt").exists(), "v1.9.0 terminal guide")
require("test_governance_approves_complete_human_review" in tests, "approval regression test")
require("test_review_history_detects_tampering" in tests, "tamper regression test")
require("test_governance_blocks_reviewed_and_public_export_before_approval" in tests, "export restriction regression test")
require("v1.9.0 — Decision Governance and Review Center" in (ROOT / "docs/ROADMAP.md").read_text(), "canonical roadmap updated")
print("Release integrity checks passed.")
