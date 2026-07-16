#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v1.15.0."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "wordpress-plugin" / "sustainable-catalyst-decision-studio"
VERSION = "1.15.0"
BUILD = "scds-v1.15.0-public-api-embeds-institutional-integration"
SOURCE = "release-v1.15.0"
PACKET = "scds-decision-packet/1.8"
DB = "1.9.0"
SCHEMAS = {
    "public_api": "scds-public-api/1.0",
    "embed_descriptor": "scds-embed-descriptor/1.0",
    "institutional_archive": "scds-institutional-archive/1.0",
    "webhook_event": "scds-webhook-event/1.0",
    "sdk_contract": "scds-cross-product-sdk/1.0",
    "platform_core_gateway": "scds-platform-core-gateway/1.0",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


main = (ROOT / "backend/app/main.py").read_text(encoding="utf-8")
module = (ROOT / "backend/app/public_integration.py").read_text(encoding="utf-8")
render = (ROOT / "backend/render.yaml").read_text(encoding="utf-8")
php = (PLUGIN / "sustainable-catalyst-decision-studio.php").read_text(encoding="utf-8")
js = (PLUGIN / "assets/js/scds-decision-studio.js").read_text(encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")
plugin_readme = (PLUGIN / "readme.txt").read_text(encoding="utf-8")
roadmap = (ROOT / "docs/ROADMAP.md").read_text(encoding="utf-8")
changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
doc = (ROOT / "docs/V1150_PUBLIC_API_EMBEDS_INSTITUTIONAL_INTEGRATION.md").read_text(encoding="utf-8")

require(f'APP_VERSION = "{VERSION}"' in main, "backend version")
require(f'DECISION_PACKET_SCHEMA = "{PACKET}"' in main, "Decision Packet 1.8")
require(BUILD in main and BUILD in render and BUILD in php, "build fingerprint parity")
require(SOURCE in main and SOURCE in render and SOURCE in php, "source identity parity")
require("rootDir: backend" in render and "healthCheckPath: /health" in render, "Render root/health")
require("value: 3.12.11" in render, "Render Python 3.12")
require(' * Version: 1.15.0' in php and "const VERSION = '1.15.0';" in php, "WordPress version")
require("const DB_VERSION = '1.9.0';" in php, "WordPress database 1.9.0")
require("Stable tag: 1.15.0" in plugin_readme, "plugin readme stable tag")
require("VERSION=\"1.15.0\"" in (ROOT / "scripts/build_release.sh").read_text(), "release packaging version")

schema_constants = {
    "public_api": "PUBLIC_API_SCHEMA",
    "embed_descriptor": "EMBED_DESCRIPTOR_SCHEMA",
    "institutional_archive": "INSTITUTIONAL_ARCHIVE_SCHEMA",
    "webhook_event": "WEBHOOK_EVENT_SCHEMA",
    "sdk_contract": "SDK_CONTRACT_SCHEMA",
    "platform_core_gateway": "PLATFORM_CORE_GATEWAY_SCHEMA",
}
for key, schema in SCHEMAS.items():
    require(schema_constants[key] in main, f"backend schema import {key}")
    require(schema in module, f"module schema {key}")
    require(schema in php, f"WordPress schema {key}")

for route in [
    "/api/v1/capabilities", "/api/v1/sdk/contracts", "/api/v1/public-dossier",
    "/api/v1/embeds/readiness", "/api/v1/embeds/scenario",
    "/api/v1/packets/export", "/api/v1/packets/import", "/api/v1/archive",
    "/api/v1/platform-core/gateway", "/api/v1/events",
    "/decision-packet/institutional-integration",
]:
    require(route in main, f"backend route {route}")

for marker in [
    "SCDS_INSTITUTIONAL_API_KEYS", "SCDS_EXPORT_SIGNING_SECRET", "X-SCDS-API-Key",
    "packet:read", "packet:write", "archive:write", "gateway:write", "event:emit",
    "MAX_BULK_PACKETS = 100", "external_delivery_attempted",
]:
    require(marker in main or marker in module, f"backend integration marker {marker}")

for marker in [
    "restPublicApiCapabilitiesUrl", "restSdkContractsUrl", "restPublicDossierUrl",
    "restReadinessEmbedUrl", "restScenarioEmbedUrl", "restInstitutionalArchiveUrl",
    "restPlatformCoreGatewayUrl", "restInternalEventUrl", "restDecisionPacketIntegrationUrl",
    'data-scds-panel="integration"', 'mode="integration"', "institutional_integration_json",
    "signed_manifest_json", "render_admin_public_api_integration",
]:
    require(marker in php, f"WordPress integration marker {marker}")

for marker in [
    "runIntegration", "loadSdkContracts", "downloadIntegration",
    "restPublicDossierUrl", "restReadinessEmbedUrl", "restScenarioEmbedUrl",
    "institutionalIntegration", "scds-decision-packet/1.8",
]:
    require(marker in js, f"browser integration marker {marker}")

manifest = load(ROOT / "data/decision_studio_release_manifest_v1.15.0.json")
plugin_manifest = load(PLUGIN / "data/release_manifest_v1.15.0.json")
integrations = load(ROOT / "data/decision_studio_integrations_v1.15.0.json")
plugin_integrations = load(PLUGIN / "data/decision_studio_integrations_v1.15.0.json")
contract = load(ROOT / "data/public_api_integration_contract_v1.15.0.json")
contract_instance = load(ROOT / "data/public_api_integration_contract_instance_v1.15.0.json")
sample = load(ROOT / "data/public_api_integration_sample_v1.15.0.json")

require(manifest == plugin_manifest, "release manifest parity")
require(integrations == plugin_integrations, "integration catalog parity")
require(manifest["release"] == VERSION and manifest["schemas"]["decision_packet"] == PACKET, "manifest identity")
require(manifest["wordpress"]["database_version"] == DB, "manifest database version")
for key, schema in SCHEMAS.items():
    require(manifest["schemas"][key] == schema, f"manifest schema {key}")
require(contract_instance["release"] == VERSION and contract_instance["decision_packet_schema"] == PACKET, "contract instance identity")
require(set(contract_instance["contracts"].values()) == set(SCHEMAS.values()), "contract schema catalog")
require(sample["public_dossier"]["schema"] == SCHEMAS["public_api"], "sample public dossier")
require(sample["readiness_embed"]["schema"] == SCHEMAS["embed_descriptor"], "sample readiness embed")
require(sample["scenario_embed"]["schema"] == SCHEMAS["embed_descriptor"], "sample scenario embed")
require(sample["institutional_archive"]["archive"]["schema"] == SCHEMAS["institutional_archive"], "sample archive")
require(sample["platform_core_gateway"]["schema"] == SCHEMAS["platform_core_gateway"], "sample gateway")
require(sample["internal_event"]["schema"] == SCHEMAS["webhook_event"], "sample event")
serialized = json.dumps(sample["public_dossier"]).lower()
require("private@example.com" not in serialized and "must never appear publicly" not in serialized, "sample public privacy")
require(sample["readiness_embed"]["security"]["scripts_included"] is False, "script-free readiness embed")
require(sample["scenario_embed"]["security"]["scripts_included"] is False, "script-free scenario embed")
require(contract["properties"]["release"]["const"] == VERSION, "contract schema release")

for marker in [
    "v1.15.0", "scds-decision-packet/1.8", "SCDS_INSTITUTIONAL_API_KEYS",
    "SCDS_EXPORT_SIGNING_SECRET", "Public API, Embeds, and Institutional Integration",
]:
    require(marker in readme + doc + changelog + roadmap, f"documentation marker {marker}")
require("v1.16.0 — Accessibility, Offline Use, and Release Hardening" in roadmap, "next roadmap release")
require("114 tests" in changelog, "test count documentation")

# Parse every JSON file and ensure exact v1.15 assets are mirrored.
json_files = [p for p in ROOT.rglob("*.json") if ".git" not in p.parts]
for path in json_files:
    load(path)
for name in [
    "public_api_integration_contract_v1.15.0.json",
    "public_api_integration_contract_instance_v1.15.0.json",
    "public_api_integration_sample_v1.15.0.json",
]:
    require(load(ROOT / "data" / name) == load(PLUGIN / "data" / name), f"plugin data parity {name}")

# No current source may generate the old Decision Packet schema.
for path in [ROOT / "backend/app/main.py", ROOT / "backend/app/public_integration.py", PLUGIN / "sustainable-catalyst-decision-studio.php", PLUGIN / "assets/js/scds-decision-studio.js"]:
    require("scds-decision-packet/1.7" not in path.read_text(encoding="utf-8"), f"stale packet marker in {path.name}")

print(f"Decision Studio v{VERSION} release-integrity checks passed. Validated {len(json_files)} JSON files.")
