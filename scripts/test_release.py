#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v1.12.0."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "wordpress-plugin/sustainable-catalyst-decision-studio"
PLUGIN_PHP = PLUGIN_ROOT / "sustainable-catalyst-decision-studio.php"
VERSION = "1.12.0"
BUILD = "scds-v1.12.0-institutional-domain-decision-packs"
SOURCE = "release-v1.12.0"
PACKET_SCHEMA = "scds-decision-packet/1.5"
PACK_SCHEMA = "scds-institutional-decision-pack/1.0"
APPLICATION_SCHEMA = "scds-decision-pack-application/1.0"
PACK_IDS = {
    "climate-energy-strategy",
    "infrastructure-capital-investment",
    "urban-resilience",
    "sustainable-procurement",
    "responsible-ai-governance",
    "research-program-approval",
    "environmental-intervention",
    "humanitarian-development-program",
    "organizational-policy",
    "advisory-diagnostic-recommendation",
}
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
tests = (ROOT / "backend/tests/test_backend.py").read_text(encoding="utf-8")
plugin = PLUGIN_PHP.read_text(encoding="utf-8")
js = (PLUGIN_ROOT / "assets/js/scds-decision-studio.js").read_text(encoding="utf-8")
css = (PLUGIN_ROOT / "assets/css/scds-decision-studio.css").read_text(encoding="utf-8")
plugin_readme = (PLUGIN_ROOT / "readme.txt").read_text(encoding="utf-8")
render = (ROOT / "backend/render.yaml").read_text(encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")
roadmap = (ROOT / "docs/ROADMAP.md").read_text(encoding="utf-8")
changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
manifest = load_json(ROOT / "data/decision_studio_release_manifest_v1.12.0.json")
plugin_manifest = load_json(PLUGIN_ROOT / "data/release_manifest_v1.12.0.json")
integrations = load_json(ROOT / "data/decision_studio_integrations_v1.12.0.json")
pack_catalog = load_json(ROOT / "data/institutional_decision_packs_v1.12.0.json")
plugin_pack_catalog = load_json(PLUGIN_ROOT / "data/institutional_decision_packs_v1.12.0.json")
pack_contract = load_json(ROOT / "data/institutional_decision_pack_contract_v1.12.0.json")
plugin_pack_contract = load_json(PLUGIN_ROOT / "data/institutional_decision_pack_contract_v1.12.0.json")
pack_sample = load_json(ROOT / "data/institutional_decision_pack_sample_v1.12.0.json")
plugin_pack_sample = load_json(PLUGIN_ROOT / "data/institutional_decision_pack_sample_v1.12.0.json")

# Identity and deployment.
require(f'APP_VERSION = "{VERSION}"' in backend, "backend version marker")
require(f" * Version: {VERSION}" in plugin, "WordPress plugin header version")
require(f"const VERSION = '{VERSION}';" in plugin, "WordPress runtime version")
require(f"Stable tag: {VERSION}" in plugin_readme, "WordPress stable tag")
require(BUILD in backend and BUILD in plugin and BUILD in render, "build fingerprint parity")
require(SOURCE in backend and SOURCE in plugin and SOURCE in render, "source release identity parity")
require("rootDir: backend" in render and "3.12.11" in render, "Render root and Python 3.12 runtime")
require("healthCheckPath: /health" in render, "Render health check")

# Manifest and additive schema identity.
require(manifest == plugin_manifest, "repository and plugin release manifests match")
require(manifest["release"] == VERSION, "release manifest version")
require(manifest["wordpress"]["database_version"] == "1.6.0", "WordPress database migration 1.6.0")
require(manifest["schemas"]["decision_packet"] == PACKET_SCHEMA, "Decision Packet schema 1.5")
require(manifest["schemas"]["institutional_decision_pack"] == PACK_SCHEMA, "Decision Pack schema")
require(manifest["schemas"]["decision_pack_application"] == APPLICATION_SCHEMA, "Decision Pack application schema")
require(manifest["compatibility"]["packet_schema_breaking_changes"] is False, "additive packet compatibility")
require(manifest["compatibility"]["v1_11_collaboration_preserved"] is True, "v1.11 collaboration preserved")
require(manifest["compatibility"]["v1_10_scenario_studio_preserved"] is True, "v1.10 scenario studio preserved")
require(manifest["compatibility"]["v1_9_governance_preserved"] is True, "v1.9 governance preserved")
require(manifest["compatibility"]["legacy_artifact_adapters_preserved"] is True, "legacy adapters preserved")
require(set(manifest["platform_products"]) == PRODUCTS, "six current platform products retained")

# Pack contracts and catalog.
require(pack_catalog == plugin_pack_catalog, "repository and plugin pack catalogs match")
require(pack_contract == plugin_pack_contract, "repository and plugin pack contracts match")
require(pack_sample == plugin_pack_sample, "repository and plugin pack sample matches")
require(pack_catalog.get("schema") == PACK_SCHEMA, "catalog schema")
require(pack_catalog.get("release") == VERSION, "catalog release")
packs = pack_catalog.get("packs", [])
require(len(packs) == 10, "ten institutional Decision Packs")
require({item.get("id") for item in packs} == PACK_IDS, "canonical Decision Pack IDs")
for item in packs:
    require(item.get("schema") == PACK_SCHEMA, f"{item.get('id')} schema")
    for key in (
        "required_intake_fields", "criteria", "required_evidence",
        "suggested_indicators", "workbench_models", "review_roles",
        "risk_questions", "readiness_rules", "brief_templates", "boundaries",
    ):
        require(bool(item.get(key)), f"{item.get('id')} has {key}")
    require(item.get("governance_defaults", {}).get("ai_approval_allowed") is False, f"{item.get('id')} prohibits AI approval")
require(integrations["decision_packet_schema"] == PACKET_SCHEMA, "integration manifest packet schema")
require(set(integrations["institutional_domain_decision_packs"]["pack_ids"]) == PACK_IDS, "integration manifest pack IDs")
require(integrations["institutional_domain_decision_packs"]["ai_approval_allowed"] is False, "integration manifest human authority boundary")

# Backend engine, routes, and tests.
for marker in (
    'DECISION_PACK_SCHEMA = "scds-institutional-decision-pack/1.0"',
    'DECISION_PACK_APPLICATION_SCHEMA = "scds-decision-pack-application/1.0"',
    "def institutional_decision_pack_catalog",
    "def validate_institutional_decision_pack",
    "def apply_institutional_decision_pack",
    '@app.get("/decision-packs/catalog")',
    '@app.get("/decision-packs/{pack_id}")',
    '@app.post("/decision-packs/validate")',
    '@app.post("/decision-packs/apply")',
    '@app.post("/decision-packet/domain-pack")',
    'packet["criteria_registry"]',
    'packet["evidence_plan"]',
    'packet["indicator_plan"]',
    'packet["model_plan"]',
    'packet["domain_readiness_rules"]',
    'packet["domain_brief_templates"]',
    '"ai_approval_allowed": False',
    '"professional_reliance_allowed": False',
):
    require(marker in backend, f"backend marker: {marker[:70]}")
for test_marker in (
    "test_decision_pack_catalog_has_ten_institutional_domains",
    "test_decision_pack_detail_and_alias_lookup",
    "test_decision_pack_validation_identifies_missing_evidence_and_roles",
    "test_complete_decision_pack_validation_is_governance_ready",
    "test_apply_decision_pack_updates_packet_schema_and_plans",
    "test_unknown_decision_pack_returns_404",
    "test_decision_pack_is_saved_and_exported",
    "test_health_and_release_publish_decision_pack_schemas",
):
    require(test_marker in tests, f"backend regression: {test_marker}")

# WordPress persistence, routes, interface, and browser fallback.
for marker in (
    "const DB_VERSION = '1.6.0';",
    "decision_pack_json LONGTEXT",
    "private function decision_pack_catalog",
    "private function validate_decision_pack_local",
    "private function apply_decision_pack_local",
    "'/decision-packs/catalog'",
    "'/decision-packs/validate'",
    "'/decision-packs/apply'",
    "'/decision-packet/domain-pack'",
    "data-scds-panel=\"packs\"",
    "data-scds-pack-preview",
    "data-scds-pack-validate",
    "data-scds-pack-apply",
    "data-scds-pack-download",
    "decision_pack_json",
    "mode=\"packs\"",
    "'decision_packet_schema'=>'scds-decision-packet/1.5'",
    "'institutional_domain_decision_packs'=>true",
    "'regulated_assurance_prohibited'=>true",
):
    require(marker in plugin, f"WordPress marker: {marker[:70]}")
for marker in (
    "function decisionPackPayload",
    "function renderDecisionPack",
    "function previewDecisionPack",
    "function runDecisionPack",
    "function downloadDecisionPack",
    "restDecisionPacksCatalogUrl",
    "restDecisionPackValidateUrl",
    "restDecisionPackApplyUrl",
    "decision_pack:decisionPack",
    "decision_pack_json:snap.decision_pack",
):
    require(marker in js, f"browser fallback marker: {marker}")
require("v1.12.0 Institutional and Domain Decision Packs" in css, "Decision Pack CSS release block")

# Documentation and release files.
require("Institutional and Domain Decision Packs" in readme and VERSION in readme, "README release identity")
require("v1.12.0 — Institutional and Domain Decision Packs" in roadmap, "canonical roadmap current release")
require("v1.13.0 — Decision Briefing and Publication Studio" in roadmap, "next canonical release")
require("1.12.0 — Institutional and Domain Decision Packs" in changelog, "changelog release entry")
require((ROOT / "docs/V1120_INSTITUTIONAL_DOMAIN_DECISION_PACKS.md").exists(), "v1.12.0 architecture documentation")
require((ROOT / "terminal/V1120_INSTITUTIONAL_DOMAIN_DECISION_PACKS_COMMANDS.txt").exists(), "v1.12.0 terminal guide")
require('VERSION="1.12.0"' in (ROOT / "scripts/build_release.sh").read_text(encoding="utf-8"), "release packaging version")

print("Decision Studio v1.12.0 release integrity checks passed.")
