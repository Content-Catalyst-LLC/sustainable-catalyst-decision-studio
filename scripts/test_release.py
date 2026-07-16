#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v1.8.0."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.8.0"
BUILD = "scds-v1.8.0-unified-evidence"
PACKET_SCHEMA = "scds-decision-packet/1.1"
ARTIFACT_SCHEMA = "scds-platform-artifact/1.0"
EVIDENCE_SCHEMA = "scds-evidence-record/1.0"
PRODUCTS = (
    "knowledge-library",
    "research-librarian",
    "site-intelligence",
    "workbench",
    "research-lab",
    "platform-core",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")
    print(f"PASS: {message}")


backend = (ROOT / "backend/app/main.py").read_text()
plugin_path = ROOT / "wordpress-plugin/sustainable-catalyst-decision-studio/sustainable-catalyst-decision-studio.php"
plugin = plugin_path.read_text()
plugin_js = (plugin_path.parent / "assets/js/scds-decision-studio.js").read_text()
plugin_readme = (plugin_path.parent / "readme.txt").read_text()
render = (ROOT / "backend/render.yaml").read_text()
manifest_path = ROOT / "data/decision_studio_release_manifest_v1.8.0.json"
plugin_manifest_path = plugin_path.parent / "data/release_manifest_v1.8.0.json"
manifest = json.loads(manifest_path.read_text())
plugin_manifest = json.loads(plugin_manifest_path.read_text())
contracts = json.loads((ROOT / "data/platform_handoff_contracts_v1.8.0.json").read_text())
samples = json.loads((ROOT / "data/sample_platform_artifacts_v1.8.0.json").read_text())

require(f'APP_VERSION = "{VERSION}"' in backend, "backend version marker")
require(f" * Version: {VERSION}" in plugin, "WordPress plugin header version")
require(f"const VERSION = '{VERSION}';" in plugin, "WordPress runtime version")
require(f"Stable tag: {VERSION}" in plugin_readme, "WordPress stable tag")
require(f'BUILD_FINGERPRINT = os.getenv("SCDS_BUILD_FINGERPRINT", "{BUILD}")' in backend, "backend build fingerprint")
require(f"const BUILD_FINGERPRINT = '{BUILD}';" in plugin, "WordPress build fingerprint")
require(manifest == plugin_manifest, "repository and plugin manifests match")
require(manifest["release"] == VERSION, "manifest release version")
require(manifest["schemas"]["decision_packet"] == PACKET_SCHEMA, "Decision Packet schema")
require(manifest["schemas"]["platform_artifact"] == ARTIFACT_SCHEMA, "platform artifact schema")
require(manifest["schemas"]["evidence_record"] == EVIDENCE_SCHEMA, "evidence record schema")
require(manifest["compatibility"]["packet_schema_breaking_changes"] is False, "additive packet compatibility declaration")
require(manifest["compatibility"]["legacy_artifact_adapters_preserved"] is True, "legacy adapter compatibility declaration")
require(set(manifest["platform_products"]) == set(PRODUCTS), "six current platform products declared")
require(len(contracts["contracts"]) == 6, "six platform handoff contracts")
require(len(samples) == 6, "six typed platform sample artifacts")
require(all(item.get("artifact_schema") == ARTIFACT_SCHEMA for item in samples), "sample artifact schema identity")
require(all((item.get("provenance") or {}).get("integrity_hash", "").startswith("sha256:") for item in samples), "sample integrity hashes")

for schema in (PACKET_SCHEMA, ARTIFACT_SCHEMA, EVIDENCE_SCHEMA):
    require(schema in backend, f"backend schema marker: {schema}")
    require(schema in plugin or schema == EVIDENCE_SCHEMA and "scds-evidence-record/1.0" in plugin, f"plugin schema marker: {schema}")
for product in PRODUCTS:
    require(product in backend, f"backend product contract: {product}")
    require(product in plugin, f"WordPress product contract: {product}")
    require(product in plugin_js, f"browser fallback product contract: {product}")

for route in (
    "/integrations/platform",
    "/integrations/contracts",
    "/integrations/validate",
    "/integrations/import-batch",
    "/decision-packet/platform-handoffs",
):
    require(route in backend, f"backend route: {route}")
    require(f"'{route}'" in plugin, f"WordPress route: {route}")

require("max_length=100" in backend and "artifacts[:100]" in backend, "backend batch import limit")
require("array_slice($this->arr($payload['artifacts']??[]),0,100)" in plugin.replace(" ", ""), "WordPress batch import limit")
require("_canonical_hash" in backend and "canonical_hash" in plugin, "canonical integrity hashing")
require("transformation_history" in backend and "transformation_history" in plugin, "transformation history preservation")
require("normalizeTypedLocal" in plugin_js, "browser typed import fallback")
require("Load Knowledge Library Sample" in plugin, "Knowledge Library sample control")

require("rootDir: backend" in render, "Render backend root directory")
require("buildCommand: pip install -r requirements.txt" in render, "Render build command")
require("startCommand: uvicorn app.main:app" in render, "Render startup command")
require("healthCheckPath: /health" in render, "Render health check")
require("add_action('plugins_loaded', [__CLASS__, 'maybe_upgrade']);" in plugin, "WordPress upgrade hook")
require("public static function maybe_upgrade()" in plugin, "WordPress migration routine")
require("add_filter('rest_pre_dispatch'" in plugin, "WordPress request guard")
require("/release" in backend and "'/release'" in plugin, "release endpoints")
require("version-mismatch" in plugin, "backend parity state")
for shortcode in ("sc_decision_studio", "sustainable_catalyst_platform", "sustainable_catalyst_platform_cta"):
    require(f"add_shortcode('{shortcode}'" in plugin, f"shortcode preserved: {shortcode}")
require((ROOT / "backend/app/__init__.py").exists(), "backend package marker")
require((ROOT / "backend/tests/__init__.py").exists(), "test package marker")
require((ROOT / "backend/pytest.ini").exists(), "pytest configuration")
require((ROOT / "docs/V180_UNIFIED_EVIDENCE_PLATFORM_HANDOFFS.md").exists(), "v1.8.0 architecture documentation")
require((ROOT / "terminal/V180_UNIFIED_EVIDENCE_PLATFORM_HANDOFFS_COMMANDS.txt").exists(), "v1.8.0 terminal guide")
print("Release integrity checks passed.")
