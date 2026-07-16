#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v1.16.0."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "wordpress-plugin" / "sustainable-catalyst-decision-studio"
VERSION = "1.16.0"
BUILD = "scds-v1.16.0-accessibility-offline-release-hardening"
SOURCE = "release-v1.16.0"
PACKET = "scds-decision-packet/1.9"
DB = "2.0.0"
SCHEMAS = {
    "accessibility_audit": "scds-accessibility-audit/1.0",
    "offline_workspace": "scds-offline-workspace/1.0",
    "release_readiness": "scds-release-readiness/1.0",
    "recovery_snapshot": "scds-recovery-snapshot/1.0",
    "migration_assessment": "scds-migration-assessment/1.0",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


main = (ROOT / "backend/app/main.py").read_text(encoding="utf-8")
module = (ROOT / "backend/app/release_hardening.py").read_text(encoding="utf-8")
render = (ROOT / "backend/render.yaml").read_text(encoding="utf-8")
php = (PLUGIN / "sustainable-catalyst-decision-studio.php").read_text(encoding="utf-8")
js = (PLUGIN / "assets/js/scds-decision-studio.js").read_text(encoding="utf-8")
offline_js = (PLUGIN / "assets/js/scds-offline-workspace.js").read_text(encoding="utf-8")
css = (PLUGIN / "assets/css/scds-decision-studio.css").read_text(encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")
plugin_readme = (PLUGIN / "readme.txt").read_text(encoding="utf-8")
roadmap = (ROOT / "docs/ROADMAP.md").read_text(encoding="utf-8")
changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
doc = (ROOT / "docs/V1160_ACCESSIBILITY_OFFLINE_RELEASE_HARDENING.md").read_text(encoding="utf-8")

require(f'APP_VERSION = "{VERSION}"' in main, "backend version")
require(f'DECISION_PACKET_SCHEMA = "{PACKET}"' in main, "Decision Packet 1.9")
require(BUILD in main and BUILD in render and BUILD in php, "build fingerprint parity")
require(SOURCE in main and SOURCE in render and SOURCE in php, "source identity parity")
require("rootDir: backend" in render and "healthCheckPath: /health" in render, "Render root/health")
require("value: 3.12.11" in render, "Render Python 3.12")
require(' * Version: 1.16.0' in php and "const VERSION = '1.16.0';" in php, "WordPress version")
require("const DB_VERSION = '2.0.0';" in php, "WordPress database 2.0.0")
require("Stable tag: 1.16.0" in plugin_readme, "plugin readme stable tag")
require('VERSION="1.16.0"' in (ROOT / "scripts/build_release.sh").read_text(), "release packaging version")

schema_constants = {
    "accessibility_audit": "ACCESSIBILITY_AUDIT_SCHEMA",
    "offline_workspace": "OFFLINE_WORKSPACE_SCHEMA",
    "release_readiness": "RELEASE_READINESS_SCHEMA",
    "recovery_snapshot": "RECOVERY_SNAPSHOT_SCHEMA",
    "migration_assessment": "MIGRATION_ASSESSMENT_SCHEMA",
}
for key, schema in SCHEMAS.items():
    require(schema_constants[key] in main, f"backend schema import {key}")
    require(schema in module, f"module schema {key}")
    require(schema in php, f"WordPress schema {key}")

for route in [
    "/release-hardening/template",
    "/release-hardening/accessibility-audit",
    "/release-hardening/offline-manifest",
    "/release-hardening/recovery-snapshot",
    "/release-hardening/migration-assessment",
    "/release-hardening/readiness",
    "/decision-packet/release-hardening",
]:
    require(route in main, f"backend route {route}")
    require(route in php, f"WordPress route {route}")

for marker in [
    "human_release_authorization_required",
    "automatic_deployment_allowed",
    "automatic_write_replay",
    "manual_compare_and_confirm",
    "sensitive_fields_removed",
    "additive_defaulting",
    "screen-reader",
]:
    require(marker in main + module + php + readme + doc, f"hardening marker {marker}")

for marker in [
    "restAccessibilityAuditUrl",
    "restOfflineManifestUrl",
    "restRecoverySnapshotUrl",
    "restMigrationAssessmentUrl",
    "restReleaseReadinessUrl",
    'data-scds-panel="hardening"',
    'mode="hardening"',
    "release_hardening_json",
    "recovery_snapshot_json",
    "render_admin_release_hardening",
]:
    require(marker in php, f"WordPress hardening marker {marker}")

for marker in [
    "runHardening",
    "hardeningPayload",
    "downloadHardening",
    "restAccessibilityAuditUrl",
    "restReleaseReadinessUrl",
    "scds-decision-packet/1.9",
    "scds_recovery_snapshot_v1_16_0",
]:
    require(marker in js, f"browser hardening marker {marker}")

for marker in [
    "indexedDB",
    "localStorage",
    "setInterval",
    "navigator.onLine",
    "SENSITIVE",
    "AUTOMATIC_WRITE_REPLAY",
]:
    require(marker in offline_js, f"offline workspace marker {marker}")

for marker in [":focus-visible", "prefers-reduced-motion", "forced-colors", "min-height:44px", "max-width:720px"]:
    require(marker in css, f"accessibility CSS marker {marker}")

manifest = load(ROOT / "data/decision_studio_release_manifest_v1.16.0.json")
plugin_manifest = load(PLUGIN / "data/release_manifest_v1.16.0.json")
integrations = load(ROOT / "data/decision_studio_integrations_v1.16.0.json")
plugin_integrations = load(PLUGIN / "data/decision_studio_integrations_v1.16.0.json")
sample = load(ROOT / "data/release_hardening_sample_v1.16.0.json")

require(manifest == plugin_manifest, "release manifest parity")
require(integrations == plugin_integrations, "integration catalog parity")
require(manifest["release"] == VERSION and manifest["schemas"]["decision_packet"] == PACKET, "manifest identity")
require(manifest["wordpress"]["database_version"] == DB, "manifest database version")
for key, schema in SCHEMAS.items():
    require(manifest["schemas"][key] == schema, f"manifest schema {key}")
require(sample["version"] == VERSION, "sample version")
require(sample["release_hardening"]["accessibility_audit"]["schema"] == SCHEMAS["accessibility_audit"], "sample accessibility")
require(sample["release_hardening"]["offline_workspace"]["schema"] == SCHEMAS["offline_workspace"], "sample offline")
require(sample["release_hardening"]["release_readiness"]["status"] == "release_candidate_ready", "sample readiness")
require(sample["recovery_snapshot"]["packet"].get("api_key") == "[removed]", "sample secret stripping")
require(sample["decision_packet"]["decision_packet_schema"] == PACKET, "sample packet schema")

for name in [
    "accessibility_audit_contract_v1.16.0.json",
    "offline_workspace_contract_v1.16.0.json",
    "release_readiness_contract_v1.16.0.json",
    "recovery_snapshot_contract_v1.16.0.json",
    "migration_assessment_contract_v1.16.0.json",
    "release_hardening_sample_v1.16.0.json",
]:
    require(load(ROOT / "data" / name) == load(PLUGIN / "data" / name), f"plugin data parity {name}")

for marker in [
    "v1.16.0",
    "scds-decision-packet/1.9",
    "Accessibility, Offline Use, and Release Hardening",
    "124 tests",
    "v2.0.0 — Connected Decision Intelligence Platform",
]:
    require(marker in readme + doc + changelog + roadmap, f"documentation marker {marker}")

# Preserve v1.15 public integration sources and endpoints.
public_module = (ROOT / "backend/app/public_integration.py").read_text(encoding="utf-8")
for marker in ["scds-public-api/1.0", "scds-embed-descriptor/1.0", "/api/v1/public-dossier", "/api/v1/archive"]:
    require(marker in public_module + main, f"v1.15 integration preservation {marker}")

json_files = [p for p in ROOT.rglob("*.json") if ".git" not in p.parts]
for path in json_files:
    load(path)

# Current source must not generate the prior packet schema except in explicit migration examples.
for path in [ROOT / "backend/app/main.py", PLUGIN / "assets/js/scds-decision-studio.js"]:
    require("scds-decision-packet/1.8" not in path.read_text(encoding="utf-8"), f"stale runtime packet marker in {path.name}")

print(f"Decision Studio v{VERSION} release-integrity checks passed. Validated {len(json_files)} JSON files.")
