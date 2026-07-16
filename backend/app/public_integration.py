from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
import hashlib
import hmac
import json
import os
import re

from pydantic import BaseModel, Field

PUBLIC_API_SCHEMA = "scds-public-api/1.0"
EMBED_DESCRIPTOR_SCHEMA = "scds-embed-descriptor/1.0"
INSTITUTIONAL_ARCHIVE_SCHEMA = "scds-institutional-archive/1.0"
WEBHOOK_EVENT_SCHEMA = "scds-webhook-event/1.0"
SDK_CONTRACT_SCHEMA = "scds-cross-product-sdk/1.0"
PLATFORM_CORE_GATEWAY_SCHEMA = "scds-platform-core-gateway/1.0"

MAX_BULK_PACKETS = 100


class PublicIntegrationRequest(BaseModel):
    packet: Dict[str, Any] = Field(default_factory=dict)
    packets: List[Dict[str, Any]] = Field(default_factory=list, max_length=MAX_BULK_PACKETS)
    title: str = ""
    audience: str = "public"
    embedType: str = "readiness"
    publicSlug: str = ""
    includeProvenance: bool = True
    includeMethodology: bool = True
    actor: str = ""
    actorRole: str = ""
    target: str = ""
    eventType: str = "decision_packet.updated"
    payload: Dict[str, Any] = Field(default_factory=dict)
    archiveLabel: str = "Institutional Decision Archive"
    notes: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha256(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _strip_private(value: Any) -> Any:
    private_keys = {
        "email", "phone", "address", "token", "api_key", "secret", "nonce",
        "private_notes", "internal_notes", "raw_artifact", "module_artifacts_raw",
        "room_members", "members", "reviewer_email", "owner_email", "invitation_token",
    }
    if isinstance(value, dict):
        cleaned: Dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized in private_keys or any(fragment in normalized for fragment in ("password", "secret", "token_hash")):
                continue
            if normalized.startswith("private_") or normalized.startswith("internal_"):
                continue
            cleaned[key] = _strip_private(item)
        return cleaned
    if isinstance(value, list):
        return [_strip_private(item) for item in value]
    if isinstance(value, str):
        return re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[redacted-email]", value, flags=re.I)
    return value


def governance_public_allowed(packet: Dict[str, Any]) -> bool:
    governance = _dict(packet.get("governance_center"))
    gate = _dict(governance.get("export_gate"))
    if gate.get("public_export_allowed") is True:
        return True
    return str(governance.get("current_state") or "").lower() in {"approved", "implemented"}


def methodology_record(packet: Dict[str, Any]) -> Dict[str, Any]:
    applied = _dict(packet.get("institutional_decision_pack"))
    methodologies = _list(packet.get("methodologies"))
    return {
        "decision_pack": {
            "pack_id": applied.get("pack_id") or applied.get("id") or "",
            "pack_name": applied.get("pack_name") or applied.get("name") or "",
            "pack_version": applied.get("pack_version") or "",
            "criteria": applied.get("criteria", packet.get("criteria_registry", [])),
            "readiness_rules": applied.get("readiness_rules", packet.get("domain_readiness_rules", [])),
            "boundaries": applied.get("boundaries", []),
        },
        "methodologies": methodologies,
        "calculation_methods": _list(_dict(packet.get("audit_and_provenance")).get("calculation_trace")) or _list(packet.get("calculation_trace")),
    }


def provenance_record(packet: Dict[str, Any]) -> Dict[str, Any]:
    audit = _dict(packet.get("audit_and_provenance"))
    return {
        "source_count": len(_list(packet.get("sources"))) + len(_list(packet.get("evidence_registry"))),
        "evidence_ledger_count": len(_list(packet.get("evidence_ledger"))),
        "integrity_checks": _list(packet.get("integrity_checks")),
        "source_ledger": _list(audit.get("source_ledger")),
        "module_artifact_ledger": _list(audit.get("module_artifact_ledger")),
        "review_status": audit.get("review_status", {}),
    }


def public_dossier(packet: Dict[str, Any], *, app_version: str, packet_schema: str, include_provenance: bool = True, include_methodology: bool = True) -> Dict[str, Any]:
    if not governance_public_allowed(packet):
        return {
            "ok": False,
            "version": app_version,
            "error": "public_release_blocked",
            "message": "Public-safe dossier generation requires an approved or implemented governance state.",
        }
    project = _dict(packet.get("project"))
    readiness = _dict(packet.get("brief_readiness") or packet.get("readiness"))
    scenario = _dict(packet.get("scenario_studio"))
    publication = _dict(packet.get("publication_studio"))
    monitoring = _dict(packet.get("outcome_monitoring"))
    dossier: Dict[str, Any] = {
        "schema": PUBLIC_API_SCHEMA,
        "version": app_version,
        "decision_packet_schema": packet_schema,
        "generated_at": utc_now(),
        "decision_packet_id": packet.get("decision_packet_id", "SCDS-PUBLIC"),
        "title": project.get("project_name") or packet.get("title") or "Public Decision Dossier",
        "decision_question": project.get("decision_question") or _dict(packet.get("decision_framing")).get("decision_question", ""),
        "governance": {
            "state": _dict(packet.get("governance_center")).get("current_state", "approved"),
            "approved_at": _dict(packet.get("governance_center")).get("approved_at", ""),
            "public_export_allowed": True,
        },
        "readiness": {
            "percent": readiness.get("readiness_percent"),
            "status": readiness.get("status") or readiness.get("readiness_status"),
            "open_issue_count": len(_list(readiness.get("open_issues"))) + len(_list(readiness.get("blocking_issues"))),
        },
        "scenario_summary": {
            "ranked_alternatives": _list(scenario.get("ranked_alternatives"))[:10],
            "dominance_analysis": _list(scenario.get("dominance_analysis"))[:10],
            "threshold_summary": _dict(scenario.get("threshold_analysis")),
        },
        "publication": {
            "publication_id": publication.get("publication_id", ""),
            "publication_type": publication.get("publication_type", "public_decision_dossier"),
            "title": publication.get("title", ""),
            "sections": [section for section in _list(publication.get("sections")) if isinstance(section, dict) and section.get("visibility", "public") == "public"],
            "bibliography": _list(publication.get("bibliography")),
        },
        "outcomes": {
            "monitoring_status": monitoring.get("status", ""),
            "decision_status": monitoring.get("decision_status", ""),
            "summary": _dict(monitoring.get("summary")),
            "next_review_at": _dict(monitoring.get("monitoring_schedule")).get("next_review_at", ""),
        },
        "boundaries": [
            "Public dossier excludes private room, invitation, personal contact, and internal-note fields.",
            "Decision support output is not professional certification, assurance, or advice.",
        ],
    }
    if include_methodology:
        dossier["methodology"] = methodology_record(packet)
    if include_provenance:
        dossier["provenance"] = provenance_record(packet)
    dossier = _strip_private(dossier)
    dossier["content_hash"] = sha256(dossier)
    return {"ok": True, "version": app_version, "public_dossier": dossier}


def readiness_embed(packet: Dict[str, Any], *, app_version: str) -> Dict[str, Any]:
    readiness = _dict(packet.get("brief_readiness") or packet.get("readiness"))
    governance = _dict(packet.get("governance_center"))
    payload = {
        "decision_packet_id": packet.get("decision_packet_id", "SCDS-DRAFT"),
        "title": _dict(packet.get("project")).get("project_name") or "Decision readiness",
        "readiness_percent": readiness.get("readiness_percent", 0),
        "status": readiness.get("status") or readiness.get("readiness_status") or "not evaluated",
        "governance_state": governance.get("current_state", "draft"),
        "reviewed_export_allowed": _dict(governance.get("export_gate")).get("reviewed_export_allowed", False),
        "public_export_allowed": _dict(governance.get("export_gate")).get("public_export_allowed", False),
    }
    descriptor = {
        "schema": EMBED_DESCRIPTOR_SCHEMA,
        "version": app_version,
        "embed_type": "readiness_summary",
        "render_mode": "data_attribute",
        "payload": _strip_private(payload),
        "html": '<div class="scds-embed scds-readiness-embed" data-scds-embed="readiness" aria-label="Decision readiness summary"></div>',
        "content_hash": sha256(payload),
        "security": {"scripts_included": False, "private_fields_included": False, "host_controls_rendering": True},
    }
    return {"ok": True, "version": app_version, "embed": descriptor}


def scenario_embed(packet: Dict[str, Any], *, app_version: str) -> Dict[str, Any]:
    scenario = _dict(packet.get("scenario_studio") or packet.get("scenario_comparison"))
    ranked = _list(scenario.get("ranked_alternatives") or scenario.get("ranked_scenarios") or scenario.get("ranking"))[:12]
    payload = {
        "decision_packet_id": packet.get("decision_packet_id", "SCDS-DRAFT"),
        "title": _dict(packet.get("project")).get("project_name") or "Scenario comparison",
        "ranked_alternatives": ranked,
        "sensitivity_summary": _list(scenario.get("one_way_sensitivity"))[:12],
        "threshold_summary": _dict(scenario.get("threshold_analysis")),
        "disclaimer": "Scenario outputs are conditional comparisons, not forecasts or guarantees.",
    }
    descriptor = {
        "schema": EMBED_DESCRIPTOR_SCHEMA,
        "version": app_version,
        "embed_type": "scenario_comparison",
        "render_mode": "data_attribute",
        "payload": _strip_private(payload),
        "html": '<div class="scds-embed scds-scenario-embed" data-scds-embed="scenario" aria-label="Decision scenario comparison"></div>',
        "content_hash": sha256(payload),
        "security": {"scripts_included": False, "private_fields_included": False, "host_controls_rendering": True},
    }
    return {"ok": True, "version": app_version, "embed": descriptor}


def sign_manifest(manifest: Dict[str, Any]) -> Dict[str, Any]:
    secret = os.getenv("SCDS_EXPORT_SIGNING_SECRET", "").strip()
    digest = hashlib.sha256(canonical_json(manifest).encode("utf-8")).hexdigest()
    result = deepcopy(manifest)
    result["manifest_digest"] = "sha256:" + digest
    if secret:
        signature = hmac.new(secret.encode("utf-8"), canonical_json(manifest).encode("utf-8"), hashlib.sha256).hexdigest()
        result.update({"signature_status": "signed", "signature_algorithm": "hmac-sha256", "signature": "hmac-sha256:" + signature})
    else:
        result.update({"signature_status": "unsigned", "signature_algorithm": "sha256-digest", "signature": ""})
    return result


def institutional_archive(packets: List[Dict[str, Any]], *, app_version: str, packet_schema: str, label: str, public_only: bool = False) -> Dict[str, Any]:
    selected = packets[:MAX_BULK_PACKETS]
    records: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for index, packet in enumerate(selected):
        if not isinstance(packet, dict):
            rejected.append({"index": index, "error": "packet_must_be_object"})
            continue
        if public_only:
            public = public_dossier(packet, app_version=app_version, packet_schema=packet_schema)
            if not public.get("ok"):
                rejected.append({"index": index, "error": public.get("error")})
                continue
            record = public["public_dossier"]
        else:
            record = deepcopy(packet)
        records.append(record)
    record_manifest = [
        {
            "index": index,
            "decision_packet_id": record.get("decision_packet_id", f"packet-{index+1}"),
            "content_hash": sha256(record),
            "packet_schema": record.get("decision_packet_schema", packet_schema),
        }
        for index, record in enumerate(records)
    ]
    manifest = sign_manifest({
        "schema": INSTITUTIONAL_ARCHIVE_SCHEMA,
        "archive_version": app_version,
        "label": label,
        "created_at": utc_now(),
        "record_count": len(records),
        "rejected_count": len(rejected),
        "public_only": public_only,
        "records": record_manifest,
    })
    archive = {
        "schema": INSTITUTIONAL_ARCHIVE_SCHEMA,
        "version": app_version,
        "label": label,
        "records": records,
        "rejected": rejected,
        "manifest": manifest,
        "machine_readable_methodology": [methodology_record(packet) for packet in selected if isinstance(packet, dict)],
        "machine_readable_provenance": [provenance_record(packet) for packet in selected if isinstance(packet, dict)],
    }
    return {"ok": True, "version": app_version, "archive": archive}


def import_archive(archive: Dict[str, Any], *, app_version: str, packet_schema: str) -> Dict[str, Any]:
    if archive.get("schema") != INSTITUTIONAL_ARCHIVE_SCHEMA:
        return {"ok": False, "version": app_version, "error": "invalid_archive_schema"}
    records = _list(archive.get("records"))[:MAX_BULK_PACKETS]
    accepted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            rejected.append({"index": index, "error": "record_must_be_object"})
            continue
        schema = record.get("decision_packet_schema") or packet_schema
        if schema != packet_schema:
            rejected.append({"index": index, "error": "unsupported_packet_schema", "schema": schema})
            continue
        accepted.append(record)
    return {
        "ok": not rejected,
        "version": app_version,
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "packets": accepted,
        "rejected": rejected,
    }


def webhook_event(event_type: str, payload: Dict[str, Any], *, app_version: str, actor: str = "", target: str = "") -> Dict[str, Any]:
    event = {
        "schema": WEBHOOK_EVENT_SCHEMA,
        "version": app_version,
        "event_id": "EVT-" + hashlib.sha256((event_type + canonical_json(payload) + utc_now()).encode("utf-8")).hexdigest()[:16].upper(),
        "event_type": event_type,
        "occurred_at": utc_now(),
        "actor": actor,
        "target": target,
        "payload": _strip_private(payload),
        "delivery": {"mode": "internal_event_record", "external_delivery_attempted": False},
    }
    event["event_hash"] = sha256(event)
    return {"ok": True, "version": app_version, "event": event}


def platform_core_gateway(packet: Dict[str, Any], payload: Dict[str, Any], *, app_version: str, packet_schema: str) -> Dict[str, Any]:
    entities = _list(payload.get("entities")) or _list(packet.get("entities"))
    ledger = _list(payload.get("evidence_ledger")) or _list(packet.get("evidence_ledger"))
    provenance = _list(payload.get("provenance_links")) or _list(packet.get("provenance_links"))
    gateway = {
        "schema": PLATFORM_CORE_GATEWAY_SCHEMA,
        "version": app_version,
        "decision_packet_schema": packet_schema,
        "decision_packet_id": packet.get("decision_packet_id", "SCDS-DRAFT"),
        "entities": entities,
        "evidence_ledger": ledger,
        "provenance_links": provenance,
        "exchange_manifest": sign_manifest({
            "decision_packet_id": packet.get("decision_packet_id", "SCDS-DRAFT"),
            "entity_count": len(entities),
            "evidence_ledger_count": len(ledger),
            "provenance_link_count": len(provenance),
            "created_at": utc_now(),
        }),
    }
    gateway["content_hash"] = sha256(gateway)
    return {"ok": True, "version": app_version, "gateway": gateway}


def sdk_contracts(*, app_version: str, packet_schema: str) -> Dict[str, Any]:
    return {
        "ok": True,
        "version": app_version,
        "schema": SDK_CONTRACT_SCHEMA,
        "api_base": "/api/v1",
        "decision_packet_schema": packet_schema,
        "authentication": {
            "header": "X-SCDS-API-Key",
            "scope_header": "X-SCDS-Requested-Scope",
            "scopes": ["packet:read", "packet:write", "archive:read", "archive:write", "gateway:write", "event:emit"],
        },
        "resources": {
            "capabilities": {"method": "GET", "path": "/api/v1/capabilities", "public": True},
            "public_dossier": {"method": "POST", "path": "/api/v1/public-dossier", "public": True},
            "readiness_embed": {"method": "POST", "path": "/api/v1/embeds/readiness", "public": True},
            "scenario_embed": {"method": "POST", "path": "/api/v1/embeds/scenario", "public": True},
            "bulk_export": {"method": "POST", "path": "/api/v1/packets/export", "scope": "packet:read"},
            "bulk_import": {"method": "POST", "path": "/api/v1/packets/import", "scope": "packet:write"},
            "archive": {"method": "POST", "path": "/api/v1/archive", "scope": "archive:write"},
            "platform_core_gateway": {"method": "POST", "path": "/api/v1/platform-core/gateway", "scope": "gateway:write"},
            "internal_event": {"method": "POST", "path": "/api/v1/events", "scope": "event:emit"},
        },
        "stability": {"breaking_changes": "new major schema only", "packet_changes": "additive within 1.x", "legacy_routes_preserved": True},
    }


def integration_template(*, app_version: str, packet_schema: str) -> Dict[str, Any]:
    return {
        "schema": PUBLIC_API_SCHEMA,
        "version": app_version,
        "decision_packet_schema": packet_schema,
        "public_surfaces": ["public_dossier", "readiness_embed", "scenario_embed", "sdk_contracts"],
        "institutional_surfaces": ["bulk_export", "bulk_import", "institutional_archive", "platform_core_gateway", "internal_events"],
        "limits": {"bulk_packets": MAX_BULK_PACKETS},
        "privacy": {"public_private_separation": True, "public_redaction": True, "institutional_api_key_required": True},
    }
