#!/usr/bin/env python3
"""Static release-integrity checks for Decision Studio v1.11.0."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.11.0"
BUILD = "scds-v1.11.0-collaborative-decision-rooms"
SOURCE = "release-v1.11.0"
PACKET_SCHEMA = "scds-decision-packet/1.4"
SCENARIO_SCHEMA = "scds-scenario-studio/1.0"
ARTIFACT_SCHEMA = "scds-platform-artifact/1.0"
EVIDENCE_SCHEMA = "scds-evidence-record/1.0"
GOVERNANCE_SCHEMA = "scds-decision-governance/1.0"
REVIEW_EVENT_SCHEMA = "scds-review-event/1.0"
ROOM_SCHEMA = "scds-collaborative-decision-room/1.0"
COLLAB_EVENT_SCHEMA = "scds-collaboration-event/1.0"
CONTACT_HANDOFF_SCHEMA = "sc-contact-engagement-handoff/1.0"
PRODUCTS = (
    "knowledge-library", "research-librarian", "site-intelligence",
    "workbench", "research-lab", "platform-core",
)
ROOM_ROLES = ("owner", "facilitator", "editor", "reviewer", "client", "observer")
BACKEND_ROUTES = (
    "/collaboration/roles", "/collaboration/template", "/collaboration/room",
    "/collaboration/action", "/collaboration/comment", "/collaboration/change-request",
    "/collaboration/snapshot", "/collaboration/share", "/collaboration/contact-handoff",
    "/decision-packet/collaboration",
)
WORDPRESS_ROUTE_MARKERS = (
    "/collaboration/template", "/collaboration/action", "/decision-packet/collaboration",
    "/rooms", "/rooms/(?P<id>\\d+)", "/rooms/(?P<id>\\d+)/action",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")
    print(f"PASS: {message}")


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


backend = (ROOT / "backend/app/main.py").read_text(encoding="utf-8")
tests = (ROOT / "backend/tests/test_backend.py").read_text(encoding="utf-8")
plugin_path = ROOT / "wordpress-plugin/sustainable-catalyst-decision-studio/sustainable-catalyst-decision-studio.php"
plugin = plugin_path.read_text(encoding="utf-8")
plugin_js = (plugin_path.parent / "assets/js/scds-decision-studio.js").read_text(encoding="utf-8")
plugin_css = (plugin_path.parent / "assets/css/scds-decision-studio.css").read_text(encoding="utf-8")
plugin_readme = (plugin_path.parent / "readme.txt").read_text(encoding="utf-8")
render = (ROOT / "backend/render.yaml").read_text(encoding="utf-8")
roadmap = (ROOT / "docs/ROADMAP.md").read_text(encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")
changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
manifest = load_json(ROOT / "data/decision_studio_release_manifest_v1.11.0.json")
plugin_manifest = load_json(plugin_path.parent / "data/release_manifest_v1.11.0.json")
room_contract = load_json(ROOT / "data/collaborative_decision_room_contract_v1.11.0.json")
plugin_room_contract = load_json(plugin_path.parent / "data/collaborative_decision_room_contract_v1.11.0.json")
room_sample = load_json(ROOT / "data/collaborative_decision_room_sample_v1.11.0.json")
plugin_room_sample = load_json(plugin_path.parent / "data/collaborative_decision_room_sample_v1.11.0.json")
integrations = load_json(ROOT / "data/decision_studio_integrations_v1.11.0.json")
governance = load_json(ROOT / "data/governance_state_catalog_v1.9.0.json")
plugin_governance = load_json(plugin_path.parent / "data/governance_state_catalog_v1.9.0.json")
scenario_contract = load_json(ROOT / "data/scenario_studio_contract_v1.10.0.json")
plugin_scenario_contract = load_json(plugin_path.parent / "data/scenario_studio_contract_v1.10.0.json")
platform_contracts = load_json(ROOT / "data/platform_handoff_contracts_v1.8.0.json")
platform_samples = load_json(ROOT / "data/sample_platform_artifacts_v1.8.0.json")

# Release identity and deployment.
require(f'APP_VERSION = "{VERSION}"' in backend, "backend version marker")
require(f" * Version: {VERSION}" in plugin, "WordPress plugin header version")
require(f"const VERSION = '{VERSION}';" in plugin, "WordPress runtime version")
require(f"Stable tag: {VERSION}" in plugin_readme, "WordPress stable tag")
require(BUILD in backend and BUILD in plugin and BUILD in render, "build fingerprint parity")
require(SOURCE in backend and SOURCE in plugin and SOURCE in render, "source release identity parity")
require("rootDir: backend" in render and "3.12.11" in render, "Render root and Python 3.12 runtime")
require("healthCheckPath: /health" in render, "Render health check")

# Manifest and additive contract identity.
require(manifest == plugin_manifest, "repository and plugin release manifests match")
require(manifest["release"] == VERSION, "manifest release version")
require(manifest["wordpress"]["database_version"] == "1.5.0", "WordPress collaboration migration version")
require(manifest["schemas"]["decision_packet"] == PACKET_SCHEMA, "Decision Packet schema 1.4")
require(manifest["schemas"]["collaboration_room"] == ROOM_SCHEMA, "room schema manifest")
require(manifest["schemas"]["collaboration_event"] == COLLAB_EVENT_SCHEMA, "collaboration event schema manifest")
require(manifest["schemas"]["contact_engagement_handoff"] == CONTACT_HANDOFF_SCHEMA, "Contact and Engagement handoff schema")
require(manifest["compatibility"]["packet_schema_breaking_changes"] is False, "additive packet compatibility")
require(manifest["compatibility"]["v1_10_scenario_studio_preserved"] is True, "v1.10 scenario layer preserved")
require(manifest["compatibility"]["v1_9_governance_preserved"] is True, "v1.9 governance preserved")
require(manifest["compatibility"]["legacy_artifact_adapters_preserved"] is True, "legacy adapters preserved")
require(set(manifest["platform_products"]) == set(PRODUCTS), "six current platform products retained")

# Collaboration contracts and fixtures.
require(room_contract == plugin_room_contract, "repository and plugin room contracts match")
require(room_sample == plugin_room_sample, "repository and plugin room samples match")
require(room_contract["schema"] == ROOM_SCHEMA, "room contract schema")
require(room_contract["event_schema"] == COLLAB_EVENT_SCHEMA, "event contract schema")
require(room_contract["decision_packet_schema"] == PACKET_SCHEMA, "room contract packet schema")
require(room_contract["canonical_persistence"] == "wordpress", "WordPress canonical room persistence")
require(tuple(item["id"] for item in room_contract["roles"]) == ROOM_ROLES, "six room roles")
require(room_contract["integrity"]["algorithm"] == "SHA-256", "SHA-256 collaboration history")
require(room_contract["privacy"]["anonymous_access"] is False, "anonymous room access disabled")
require(room_contract["privacy"]["invitation_token_storage"] == "SHA-256 hash only", "invitation token hash-only storage")
require(room_contract["governance_boundary"]["ai_approval_allowed"] is False, "AI approval prohibited")
require(room_sample["request"]["room"]["visibility"] == "private", "private sample room")
require(room_sample["expected"]["governance_approval_remains_separate"] is True, "sample retains governance boundary")
require(integrations["decision_packet_schema"] == PACKET_SCHEMA, "integration manifest packet schema")
require(integrations["collaboration_room_schema"] == ROOM_SCHEMA, "integration manifest room schema")
require(integrations["collaborative_decision_rooms"]["canonical_persistence"] == "wordpress", "integration manifest persistence authority")

# Retained earlier contracts.
require(governance == plugin_governance, "governance catalogs retained")
require(scenario_contract == plugin_scenario_contract, "scenario contracts retained")
require(scenario_contract["alternative_limit"] == 100, "100-alternative scenario cap retained")
require(len(platform_contracts["contracts"]) == 6 and len(platform_samples) == 6, "six typed platform handoffs retained")

for schema in (
    PACKET_SCHEMA, ROOM_SCHEMA, COLLAB_EVENT_SCHEMA, CONTACT_HANDOFF_SCHEMA,
    SCENARIO_SCHEMA, ARTIFACT_SCHEMA, EVIDENCE_SCHEMA, GOVERNANCE_SCHEMA, REVIEW_EVENT_SCHEMA,
):
    require(schema in backend, f"backend schema marker: {schema}")
    require(schema in plugin or schema in plugin_js, f"WordPress/browser schema marker: {schema}")

for route in BACKEND_ROUTES:
    require(route in backend, f"backend collaboration route: {route}")
for route in WORDPRESS_ROUTE_MARKERS:
    require(route in plugin, f"WordPress room route: {route}")

# Backend collaboration behavior markers.
for token in (
    "collaboration_role_catalog", "collaborative_room_template", "verify_collaboration_history",
    "compare_room_snapshots", "_room_notify", "resolve_comment", "resolve_change_request",
    "apply_revision", "invite_member", "lock_version", "reopen_version", "contact_handoff",
    "share_token_once", "approved_version_locked", "governance_approval_required",
):
    require(token in backend, f"backend collaboration behavior: {token}")

# WordPress persistence and local fallback parity.
for marker in (
    "collaboration_json LONGTEXT", "const ROOMS_TABLE = 'scds_rooms'",
    "const ROOM_MEMBERS_TABLE = 'scds_room_members'", "const ROOM_EVENTS_TABLE = 'scds_room_events'",
    "private function collaboration_notify", "verify_collaboration_history", "resolve_comment",
    "resolve_change_request", "apply_revision", "invite_member", "lock_version", "reopen_version",
    "token_hash", "share_token_once", "approved_version_locked", "contact_engagement_handoff",
    "sync_room_relations", "room_row_allowed", "render_admin_rooms",
):
    require(marker in plugin, f"WordPress collaboration marker: {marker}")
require("'collaboration_json'=>wp_json_encode" in plugin, "collaboration saved with Decision Packets")
require("collaboration_json" in backend and "room_activity_json" in backend and "snapshot_comparison_json" in backend, "backend collaboration exports")
require("collaboration_json" in plugin and "room_activity_json" in plugin and "snapshot_comparison_json" in plugin, "WordPress collaboration exports")
require("is_user_logged_in()" in plugin and "Sign-in required" in plugin, "private room sign-in gate")
require("'scds-rooms'" in plugin, "Decision Rooms admin menu")

# Browser UI behavior.
for marker in (
    "roomPayload", "runRoomAction", "saveRoom", "renderRooms", "downloadRoom",
    "data-scds-room-create", "data-scds-room-comment-add", "data-scds-room-comment-resolve",
    "data-scds-room-change-request", "data-scds-room-change-resolve", "data-scds-room-change-implement",
    "data-scds-room-apply-revision", "data-scds-room-invite", "data-scds-room-lock",
    "data-scds-room-reopen", "data-scds-room-contact-handoff",
):
    require(marker in plugin or marker in plugin_js, f"Decision Room UI behavior: {marker}")
require('mode="room"' in plugin_readme, "Decision Room shortcode documented")
require("v1.11.0 Collaborative Decision Rooms" in plugin_css, "Decision Room CSS release block")

# Existing product and governance boundaries.
for product in PRODUCTS:
    require(product in backend and product in plugin and product in plugin_js, f"typed platform product retained: {product}")
for shortcode in ("sc_decision_studio", "sustainable_catalyst_platform", "sustainable_catalyst_platform_cta"):
    require(f"add_shortcode('{shortcode}'" in plugin, f"shortcode preserved: {shortcode}")
require("governance_export_blocked" in backend and "scds_governance_export_blocked" in plugin, "governance-aware export restrictions retained")
require("probabilistic simulation" in backend and "probabilistic simulation" in plugin, "Workbench modeling boundary retained")
require("AI cannot approve" in backend and "AI cannot approve" in plugin, "human approval boundary")

# Documentation, roadmap, and regression tests.
require((ROOT / "docs/V1110_COLLABORATIVE_DECISION_ROOMS.md").exists(), "v1.11.0 architecture documentation")
require((ROOT / "terminal/V1110_COLLABORATIVE_DECISION_ROOMS_COMMANDS.txt").exists(), "v1.11.0 terminal guide")
require("v1.11.0 — Collaborative Decision Rooms" in roadmap, "canonical roadmap current release")
require("v1.12.0 — Institutional and Domain Decision Packs" in roadmap, "next roadmap release retained")
require("Collaborative Decision Rooms" in readme and "1.11.0 — Collaborative Decision Rooms" in changelog, "release documentation updated")
for test_name in (
    "test_collaboration_template_and_roles",
    "test_collaboration_room_comment_and_notifications",
    "test_collaboration_change_request_resolution_and_revision_diff",
    "test_collaboration_snapshots_compare_and_hash_chain_tamper_detection",
    "test_private_room_share_grant_hashes_token_and_exposes_once",
    "test_locked_approved_version_blocks_revision_until_reopened",
    "test_collaboration_contact_and_engagement_handoff",
    "test_collaboration_is_saved_and_exported_with_packet_schema_1_4",
    "test_collaboration_permission_denies_observer_comment",
    "test_health_and_release_publish_collaboration_schemas",
):
    require(test_name in tests, f"collaboration regression test: {test_name}")

print("Release integrity checks passed.")
