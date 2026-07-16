#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v1.13.0."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "wordpress-plugin/sustainable-catalyst-decision-studio"
PLUGIN_PHP = PLUGIN_ROOT / "sustainable-catalyst-decision-studio.php"
VERSION = "1.13.0"
BUILD = "scds-v1.13.0-decision-briefing-publication-studio"
SOURCE = "release-v1.13.0"
PACKET_SCHEMA = "scds-decision-packet/1.6"
PUBLICATION_SCHEMA = "scds-decision-publication/1.0"
HANDOFF_SCHEMA = "scds-publication-handoff/1.0"
REDACTION_SCHEMA = "scds-publication-redaction/1.0"
PUBLICATION_IDS = {
    "executive_decision_memo", "technical_decision_report", "board_leadership_brief",
    "alternatives_analysis", "public_decision_dossier", "evidence_appendix",
    "assumptions_register", "methodology_statement", "audit_provenance_appendix",
    "implementation_plan", "dissenting_view", "monitoring_plan",
}
TARGETS = {"knowledge_library", "research", "publications", "channel"}
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
doc = (ROOT / "docs/V1130_DECISION_BRIEFING_PUBLICATION_STUDIO.md").read_text(encoding="utf-8")
terminal = (ROOT / "terminal/V1130_DECISION_BRIEFING_PUBLICATION_STUDIO_COMMANDS.txt").read_text(encoding="utf-8")
manifest = load_json(ROOT / "data/decision_studio_release_manifest_v1.13.0.json")
plugin_manifest = load_json(PLUGIN_ROOT / "data/release_manifest_v1.13.0.json")
integrations = load_json(ROOT / "data/decision_studio_integrations_v1.13.0.json")
contract = load_json(ROOT / "data/decision_publication_contract_v1.13.0.json")
plugin_contract = load_json(PLUGIN_ROOT / "data/decision_publication_contract_v1.13.0.json")
sample = load_json(ROOT / "data/decision_publication_sample_v1.13.0.json")
plugin_sample = load_json(PLUGIN_ROOT / "data/decision_publication_sample_v1.13.0.json")

# Identity and deployment.
require(f'APP_VERSION = "{VERSION}"' in backend, "backend version marker")
require(f" * Version: {VERSION}" in plugin, "WordPress plugin header version")
require(f"const VERSION = '{VERSION}';" in plugin, "WordPress runtime version")
require(f"Stable tag: {VERSION}" in plugin_readme, "WordPress stable tag")
require(BUILD in backend and BUILD in plugin and BUILD in render, "build fingerprint parity")
require(SOURCE in backend and SOURCE in plugin and SOURCE in render, "source release identity parity")
require("rootDir: backend" in render and "3.12.11" in render, "Render root and Python 3.12 runtime")
require("healthCheckPath: /health" in render, "Render health check")
require('VERSION="1.13.0"' in (ROOT / "scripts/build_release.sh").read_text(), "release packaging version")

# Manifest and additive schema identity.
require(manifest == plugin_manifest, "repository and plugin release manifests match")
require(manifest["release"] == VERSION, "release manifest version")
require(manifest["wordpress"]["database_version"] == "1.7.0", "WordPress database migration 1.7.0")
require(manifest["schemas"]["decision_packet"] == PACKET_SCHEMA, "Decision Packet schema 1.6")
require(manifest["schemas"]["decision_publication"] == PUBLICATION_SCHEMA, "decision publication schema")
require(manifest["schemas"]["publication_handoff"] == HANDOFF_SCHEMA, "publication handoff schema")
require(manifest["schemas"]["publication_redaction"] == REDACTION_SCHEMA, "publication redaction schema")
require(manifest["compatibility"]["packet_schema_breaking_changes"] is False, "additive packet compatibility")
require(manifest["compatibility"]["v1_12_decision_packs_preserved"] is True, "v1.12 Decision Packs preserved")
require(manifest["compatibility"]["v1_11_collaboration_preserved"] is True, "v1.11 collaboration preserved")
require(manifest["compatibility"]["v1_10_scenario_studio_preserved"] is True, "v1.10 scenario studio preserved")
require(manifest["compatibility"]["v1_9_governance_preserved"] is True, "v1.9 governance preserved")
require(manifest["compatibility"]["legacy_artifact_adapters_preserved"] is True, "legacy adapters preserved")
require(set(manifest["platform_products"]) == PRODUCTS, "six current platform products retained")

# Publication contracts and samples.
require(contract == plugin_contract, "repository and plugin publication contracts match")
require(sample == plugin_sample, "repository and plugin publication samples match")
require(contract["properties"]["schema"]["const"] == PUBLICATION_SCHEMA, "publication contract schema identity")
require(set(contract["properties"]["publication_type"]["enum"]) == PUBLICATION_IDS, "publication contract exposes twelve types")
require(sample["schema"] == PUBLICATION_SCHEMA, "sample publication schema")
require(sample["citation_style"] == "Harvard", "sample Harvard citation style")
require(sample["content_hash"].startswith("sha256:") and len(sample["content_hash"]) == 71, "sample content hash format")
require(sample["publication_handoffs"][0]["schema"] == HANDOFF_SCHEMA, "sample publication handoff schema")
require(integrations["decision_packet_schema"] == PACKET_SCHEMA, "integration manifest packet schema")
require(integrations["decision_publication_schema"] == PUBLICATION_SCHEMA, "integration manifest publication schema")
require(set(integrations["decision_briefing_publication_studio"]["publication_types"]) == PUBLICATION_IDS, "integration manifest publication catalog")
require(set(integrations["decision_briefing_publication_studio"]["targets"]) == TARGETS, "integration manifest publication targets")

# Backend publication engine and API.
for marker in [
    'PUBLICATION_STUDIO_SCHEMA = "scds-decision-publication/1.0"',
    'PUBLICATION_HANDOFF_SCHEMA = "scds-publication-handoff/1.0"',
    'PUBLICATION_REDACTION_SCHEMA = "scds-publication-redaction/1.0"',
    'def publication_studio_template()', 'def generate_publication(',
    'def publication_markdown(', 'def publication_html(',
    '@app.get("/publication-studio/template")',
    '@app.post("/publication-studio/generate")',
    '@app.post("/publication-studio/redact")',
    '@app.post("/publication-studio/handoff")',
    '@app.post("/decision-packet/publication")',
    '"publication_studio": {}', '"publication_registry": []',
    '"publication_handoffs": []', '"redaction_log": []',
    '"publication_markdown"', '"publication_html"', '"bibliography_json"',
]:
    require(marker in backend, f"backend marker: {marker}")
require('audience == "reviewed" and not gate.get("reviewed_export_allowed"' in backend, "reviewed publication governance gate")
require('audience == "public" and not gate.get("public_export_allowed"' in backend, "public publication governance gate")
require('"citation_style": "Harvard"' in backend, "Harvard citation registry")
require('"knowledge_library"' in backend and '"channel"' in backend, "publication targets in backend")
require('"/publication-studio/template", "/publication-studio/template"' not in backend, "no duplicate publication template route in catalog")

# Backend regression coverage.
for phrase in [
    "test_publication_studio_template_has_twelve_outputs",
    "test_internal_publication_generates_harvard_citations_and_exports",
    "test_publication_redaction_masks_public_contact_data_and_private_sections",
    "test_publication_governance_blocks_reviewed_and_public_outputs",
    "test_publication_packet_schema_and_registry_are_additive",
    "test_publication_handoff_endpoint_returns_structured_targets",
    "test_publication_is_saved_and_exported",
    "test_publication_type_aliases_resolve",
    "test_health_and_release_publish_publication_schemas",
]:
    require(phrase in tests, f"backend regression test: {phrase}")

# WordPress database, routes, fallback, UI, persistence, and exports.
for marker in [
    "const DB_VERSION = '1.7.0';",
    "const PUBLICATION_STUDIO_SCHEMA = 'scds-decision-publication/1.0';",
    "const PUBLICATION_HANDOFF_SCHEMA = 'scds-publication-handoff/1.0';",
    "const PUBLICATION_REDACTION_SCHEMA = 'scds-publication-redaction/1.0';",
    "publication_json LONGTEXT",
    "render_panel_publication",
    "generate_publication_local",
    "rest_publication_template", "rest_publication_generate", "rest_publication_redact", "rest_publication_handoff",
    "'/publication-studio/template'", "'/publication-studio/generate'", "'/publication-studio/redact'", "'/publication-studio/handoff'", "'/decision-packet/publication'",
    "'publication_studio'=>[]", "'publication_registry'=>[]", "'publication_handoffs'=>[]", "'redaction_log'=>[]",
    "'publication_json'", "'publication_markdown'", "'publication_html'", "'bibliography_json'", "'redaction_json'", "'publication_handoff_json'",
    "[sc_decision_studio mode=\"publication\"",
]:
    require(marker in plugin or marker in plugin_readme, f"WordPress marker: {marker}")
require("array_is_list" not in plugin, "PHP 7.4-compatible publication array handling")
require(plugin.count("'publication_studio_schema'=>self::PUBLICATION_STUDIO_SCHEMA") >= 2, "WordPress publication schema exposed")

# Browser workspace.
for marker in [
    "function publicationPayload(root)", "function publicationOutputHtml(data)",
    "function runPublication(root,mode)", "function downloadPublication(root,kind)",
    "data-scds-publication-generate", "data-scds-publication-redact", "data-scds-publication-handoff",
    "decision-studio-publication-v1.13.0.json", "decision-studio-publication-v1.13.0.md", "decision-studio-publication-v1.13.0.html",
    "publication_studio:publicationStudio", "scds_saved_decision_packets_v1_13_0",
]:
    require(marker in js, f"browser marker: {marker}")
require("v1.12.0" not in js, "no stale v1.12 browser release filenames")
for marker in ["v1.13.0 Decision Briefing and Publication Studio", ".scds-publication-section", ".scds-publication-bibliography"]:
    require(marker in css, f"publication CSS marker: {marker}")

# Documentation and roadmap.
for text, label in [
    (readme, "repository README"), (plugin_readme, "plugin readme"),
    (roadmap, "roadmap"), (changelog, "changelog"), (doc, "publication documentation"),
    (terminal, "terminal commands"),
]:
    require(VERSION in text, f"{label} version")
require("v1.14.0 — Outcomes, Monitoring, and Reassessment" in roadmap, "next roadmap release")
require("Harvard" in doc and "redaction" in doc.lower() and "governance" in doc.lower(), "publication documentation coverage")
require("[sc_decision_studio mode=\"publication\"" in plugin_readme and "[sc_decision_studio mode=\"publication\"" in doc, "publication shortcode documentation")

print("Decision Studio v1.13.0 release-integrity checks passed.")
