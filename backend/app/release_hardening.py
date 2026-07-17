from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

ACCESSIBILITY_AUDIT_SCHEMA = "scds-accessibility-audit/1.0"
OFFLINE_WORKSPACE_SCHEMA = "scds-offline-workspace/1.0"
RELEASE_READINESS_SCHEMA = "scds-release-readiness/1.0"
RECOVERY_SNAPSHOT_SCHEMA = "scds-recovery-snapshot/1.0"
MIGRATION_ASSESSMENT_SCHEMA = "scds-migration-assessment/1.0"

SENSITIVE_KEY_PATTERN = re.compile(r"(?:api[_-]?key|secret|password|token|authorization|cookie|private[_-]?key)", re.I)


class ReleaseHardeningRequest(BaseModel):
    packet: Dict[str, Any] = Field(default_factory=dict)
    accessibilityProfile: Dict[str, Any] = Field(default_factory=dict)
    offlineProfile: Dict[str, Any] = Field(default_factory=dict)
    performanceProfile: Dict[str, Any] = Field(default_factory=dict)
    backupProfile: Dict[str, Any] = Field(default_factory=dict)
    migrationProfile: Dict[str, Any] = Field(default_factory=dict)
    snapshotLabel: str = "Decision Packet recovery snapshot"
    actor: str = ""
    notes: str = ""
    action: str = "readiness"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _strip_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: Dict[str, Any] = {}
        for key, item in value.items():
            if SENSITIVE_KEY_PATTERN.search(str(key)):
                cleaned[key] = "[removed]"
            else:
                cleaned[key] = _strip_sensitive(item)
        return cleaned
    if isinstance(value, list):
        return [_strip_sensitive(item) for item in value]
    return value


def hardening_template(app_version: str, packet_schema: str) -> Dict[str, Any]:
    return {
        "schema": RELEASE_READINESS_SCHEMA,
        "version": app_version,
        "decision_packet_schema": packet_schema,
        "accessibility": {
            "schema": ACCESSIBILITY_AUDIT_SCHEMA,
            "checks": [
                "keyboard_navigation",
                "visible_focus",
                "semantic_landmarks",
                "form_labels",
                "screen_reader_status",
                "accessible_tables",
                "accessible_chart_alternatives",
                "reduced_motion",
                "contrast_review",
                "error_identification",
                "touch_target_size",
                "zoom_and_reflow",
            ],
            "target": "WCAG 2.2 AA-oriented product validation; final conformance requires human testing.",
        },
        "offline": {
            "schema": OFFLINE_WORKSPACE_SCHEMA,
            "capabilities": [
                "local_draft_autosave",
                "recovery_snapshots",
                "offline_packet_view",
                "queued_write_intents",
                "explicit_conflict_resolution",
                "online_status_announcements",
            ],
            "boundaries": [
                "No background approval, publishing, or external delivery while offline.",
                "Institutional API credentials and private invitation tokens are never cached.",
                "Queued write intents require authenticated replay and conflict review.",
            ],
        },
        "release_gates": [
            "accessibility",
            "offline_recovery",
            "performance",
            "migration_compatibility",
            "backup_restore",
            "security_privacy",
        ],
        "supported_migrations": {
            "from_packet_schemas": [f"scds-decision-packet/1.{minor}" for minor in range(0, 10)] + ["scds-decision-packet/2.0"],
            "to_packet_schema": packet_schema,
            "strategy": "additive_defaulting_with_original_packet_preserved_in_recovery_snapshot",
        },
        "warnings": [
            "Automated checks cannot establish complete accessibility conformance.",
            "Release readiness is an engineering gate, not legal certification, assurance, or professional sign-off.",
        ],
    }


def accessibility_audit(profile: Dict[str, Any], app_version: str) -> Dict[str, Any]:
    checks = [
        ("keyboard_navigation", "All interactive controls can be reached and operated by keyboard."),
        ("visible_focus", "Keyboard focus is clearly visible."),
        ("semantic_landmarks", "Page regions use headings and semantic landmarks."),
        ("form_labels", "Form controls have programmatic labels and instructions."),
        ("screen_reader_status", "Async status and validation messages are announced."),
        ("accessible_tables", "Tables have headers and meaningful reading order."),
        ("accessible_chart_alternatives", "Charts have text or table alternatives."),
        ("reduced_motion", "Animations respect reduced-motion preferences."),
        ("contrast_review", "Text, controls, and focus indicators passed contrast review."),
        ("error_identification", "Errors identify the field and corrective action."),
        ("touch_target_size", "Primary controls meet usable touch-target sizing."),
        ("zoom_and_reflow", "Core workflows remain usable at 200% zoom and narrow widths."),
    ]
    results: List[Dict[str, Any]] = []
    passed = 0
    blockers: List[str] = []
    for key, description in checks:
        raw = profile.get(key, False)
        status = "pass" if raw is True else ("not_applicable" if str(raw).lower() in {"n/a", "not_applicable"} else "fail")
        if status in {"pass", "not_applicable"}:
            passed += 1
        else:
            blockers.append(key)
        results.append({"id": key, "description": description, "status": status, "evidence": profile.get(f"{key}_evidence", "")})
    score = round((passed / len(checks)) * 100, 1)
    audit = {
        "schema": ACCESSIBILITY_AUDIT_SCHEMA,
        "version": app_version,
        "generated_at": _utc_now(),
        "score_percent": score,
        "status": "ready_for_human_validation" if not blockers else ("needs_remediation" if score >= 60 else "blocked"),
        "checks": results,
        "blockers": blockers,
        "manual_validation_required": [
            "Screen-reader testing with at least one desktop and one mobile combination.",
            "Keyboard-only completion of intake, review, export, and recovery workflows.",
            "Zoom, reflow, contrast, and forced-colors review on representative pages.",
        ],
        "conformance_claim": "none",
    }
    audit["content_hash"] = _hash(audit)
    return audit


def offline_workspace_manifest(packet: Dict[str, Any], profile: Dict[str, Any], app_version: str, packet_schema: str) -> Dict[str, Any]:
    cacheable_assets = profile.get("cacheable_assets") or [
        "assets/css/scds-decision-studio.css",
        "assets/js/scds-decision-studio.js",
        "assets/js/scds-offline-workspace.js",
    ]
    manifest = {
        "schema": OFFLINE_WORKSPACE_SCHEMA,
        "version": app_version,
        "decision_packet_schema": packet_schema,
        "generated_at": _utc_now(),
        "decision_packet_id": packet.get("decision_packet_id", "SCDS-DRAFT"),
        "online": bool(profile.get("online", True)),
        "storage": {
            "primary": "indexeddb",
            "fallback": "localstorage",
            "maximum_drafts": int(profile.get("maximum_drafts", 25)),
            "maximum_snapshot_bytes": int(profile.get("maximum_snapshot_bytes", 5_000_000)),
            "sensitive_fields_cached": False,
        },
        "cache_policy": {
            "strategy": "network_first_for_api_cache_first_for_static_assets",
            "cacheable_assets": cacheable_assets,
            "non_cacheable": ["api_keys", "authorization_headers", "private_invitation_tokens", "institutional_archive_secrets"],
            "api_responses_cached": False,
        },
        "draft_policy": {
            "autosave_interval_seconds": int(profile.get("autosave_interval_seconds", 15)),
            "checksum_required": True,
            "recovery_snapshot_before_migration": True,
            "queued_write_intents": bool(profile.get("queued_write_intents", True)),
            "automatic_write_replay": False,
            "conflict_strategy": "manual_compare_and_confirm",
        },
        "status_announcements": {
            "online_offline_live_region": True,
            "save_success_live_region": True,
            "recovery_available_live_region": True,
        },
        "offline_capabilities": ["view_current_packet", "edit_local_draft", "create_recovery_snapshot", "export_json"],
        "online_required": ["governance_transition", "room_membership_change", "institutional_api", "publication_handoff", "external_delivery"],
    }
    manifest["content_hash"] = _hash(manifest)
    return manifest


def recovery_snapshot(packet: Dict[str, Any], label: str, actor: str, app_version: str, packet_schema: str) -> Dict[str, Any]:
    cleaned = _strip_sensitive(deepcopy(packet))
    payload = _canonical_json(cleaned)
    snapshot = {
        "schema": RECOVERY_SNAPSHOT_SCHEMA,
        "version": app_version,
        "decision_packet_schema": packet_schema,
        "snapshot_id": "snapshot-" + hashlib.sha256((payload + label + _utc_now()).encode("utf-8")).hexdigest()[:20],
        "decision_packet_id": cleaned.get("decision_packet_id", "SCDS-DRAFT") if isinstance(cleaned, dict) else "SCDS-DRAFT",
        "label": label.strip() or "Decision Packet recovery snapshot",
        "actor": actor.strip(),
        "created_at": _utc_now(),
        "size_bytes": len(payload.encode("utf-8")),
        "packet_hash": _hash(cleaned),
        "sensitive_fields_removed": True,
        "restore_strategy": "validate_schema_then_restore_as_new_draft",
        "packet": cleaned,
    }
    snapshot["snapshot_hash"] = _hash({k: v for k, v in snapshot.items() if k != "snapshot_hash"})
    return snapshot


def migration_assessment(profile: Dict[str, Any], packet: Dict[str, Any], app_version: str, packet_schema: str) -> Dict[str, Any]:
    source_schema = str(profile.get("from_schema") or packet.get("decision_packet_schema") or "scds-decision-packet/1.8")
    target_schema = str(profile.get("to_schema") or packet_schema)
    def schema_rank(value: str) -> Optional[int]:
        match = re.fullmatch(r"scds-decision-packet/(\d+)\.(\d+)", value)
        if not match:
            return None
        major, minor = int(match.group(1)), int(match.group(2))
        if major == 1 and 0 <= minor <= 9:
            return minor
        if major == 2 and minor == 0:
            return 100
        return None

    source_rank = schema_rank(source_schema)
    target_rank = schema_rank(target_schema)
    supported = source_rank is not None and target_rank is not None and source_rank <= target_rank and target_schema == packet_schema
    blockers: List[str] = []
    if source_rank is None:
        blockers.append("unrecognized_source_schema")
    elif target_rank is not None and source_rank > target_rank:
        blockers.append("downgrade_not_supported")
    if target_rank is None or target_schema != packet_schema:
        blockers.append("unsupported_target_schema")
    assessment = {
        "schema": MIGRATION_ASSESSMENT_SCHEMA,
        "version": app_version,
        "generated_at": _utc_now(),
        "from_schema": source_schema,
        "to_schema": target_schema,
        "supported": supported and not blockers,
        "strategy": "additive_defaulting",
        "required_actions": [
            "Create recovery snapshot before migration.",
            "Preserve unknown fields under migration_legacy_fields.",
            "Apply defaults only for missing v2.0.0 sections.",
            "Re-run governance and export readiness after migration.",
        ],
        "added_sections": [
            "release_hardening",
            "accessibility_audit",
            "offline_workspace",
            "recovery_snapshots",
            "migration_assessment",
            "release_readiness",
            "connected_platform",
            "lifecycle_assessment",
            "decision_intelligence_graph",
            "decision_action_queue",
            "decision_portfolio_index",
            "connected_exchange",
            "lifecycle_history",
        ],
        "blockers": blockers,
        "rollback": "Restore the pre-migration recovery snapshot as a new draft; do not overwrite the source record.",
    }
    assessment["content_hash"] = _hash(assessment)
    return assessment


def release_readiness(
    packet: Dict[str, Any],
    req: ReleaseHardeningRequest,
    app_version: str,
    packet_schema: str,
    packet_template_factory: Optional[Callable[[], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    base = packet_template_factory() if packet_template_factory else {}
    base.update(packet or {})
    base["packet_version"] = app_version
    base["decision_packet_schema"] = packet_schema

    access = accessibility_audit(req.accessibilityProfile, app_version)
    offline = offline_workspace_manifest(base, req.offlineProfile, app_version, packet_schema)
    migration = migration_assessment(req.migrationProfile, base, app_version, packet_schema)
    snapshot = recovery_snapshot(base, req.snapshotLabel, req.actor, app_version, packet_schema)

    perf = req.performanceProfile
    backup = req.backupProfile
    gates = [
        {"id": "accessibility", "status": "pass" if not access["blockers"] else "fail", "details": access["blockers"]},
        {"id": "offline_recovery", "status": "pass" if offline["draft_policy"]["checksum_required"] and snapshot["packet_hash"] else "fail", "details": []},
        {"id": "performance", "status": "pass" if bool(perf.get("large_packet_tested", False)) and bool(perf.get("mobile_tested", False)) else "fail", "details": [key for key in ["large_packet_tested", "mobile_tested"] if not perf.get(key, False)]},
        {"id": "migration_compatibility", "status": "pass" if migration["supported"] else "fail", "details": migration["blockers"]},
        {"id": "backup_restore", "status": "pass" if bool(backup.get("backup_tested", False)) and bool(backup.get("restore_tested", False)) else "fail", "details": [key for key in ["backup_tested", "restore_tested"] if not backup.get(key, False)]},
        {"id": "security_privacy", "status": "pass" if bool(req.offlineProfile.get("sensitive_cache_reviewed", False)) and bool(req.backupProfile.get("privacy_reviewed", False)) else "fail", "details": [key for key, value in {"sensitive_cache_reviewed": req.offlineProfile.get("sensitive_cache_reviewed", False), "privacy_reviewed": req.backupProfile.get("privacy_reviewed", False)}.items() if not value]},
    ]
    passed = sum(1 for gate in gates if gate["status"] == "pass")
    blockers = [gate["id"] for gate in gates if gate["status"] != "pass"]
    readiness = {
        "schema": RELEASE_READINESS_SCHEMA,
        "version": app_version,
        "decision_packet_schema": packet_schema,
        "generated_at": _utc_now(),
        "status": "release_candidate_ready" if not blockers else ("conditional" if passed >= 4 else "blocked"),
        "readiness_percent": round((passed / len(gates)) * 100, 1),
        "gates": gates,
        "blockers": blockers,
        "human_release_authorization_required": True,
        "automatic_deployment_allowed": False,
        "notes": req.notes,
        "warnings": [
            "Automated readiness cannot replace assistive-technology testing, restore drills, security review, or human release authorization.",
            "This record is not certification, assurance, legal compliance, or professional sign-off.",
        ],
    }
    readiness["content_hash"] = _hash(readiness)

    hardening = {
        "schema": RELEASE_READINESS_SCHEMA,
        "version": app_version,
        "accessibility_audit": access,
        "offline_workspace": offline,
        "migration_assessment": migration,
        "recovery_snapshot": {key: value for key, value in snapshot.items() if key != "packet"},
        "release_readiness": readiness,
    }
    hardening["content_hash"] = _hash(hardening)

    base["release_hardening"] = hardening
    base["accessibility_audit"] = access
    base["offline_workspace"] = offline
    base.setdefault("recovery_snapshots", []).append({key: value for key, value in snapshot.items() if key != "packet"})
    base["migration_assessment"] = migration
    base["release_readiness"] = readiness
    formats = base.setdefault("export_center", {}).setdefault("available_formats", [])
    for item in ["release_hardening_json", "accessibility_audit_json", "offline_workspace_json", "recovery_snapshot_json"]:
        if item not in formats:
            formats.append(item)

    return {
        "ok": True,
        "version": app_version,
        "schema": RELEASE_READINESS_SCHEMA,
        "release_hardening": hardening,
        "recovery_snapshot": snapshot,
        "decision_packet": base,
        "template": hardening_template(app_version, packet_schema),
    }
