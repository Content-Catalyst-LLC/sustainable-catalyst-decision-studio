from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
import hashlib
import json

from pydantic import BaseModel, Field

OUTCOME_MONITORING_SCHEMA = "scds-outcome-monitoring/1.0"
REASSESSMENT_EVENT_SCHEMA = "scds-reassessment-event/1.0"
DECISION_REGISTRY_SCHEMA = "scds-decision-registry-entry/1.0"


class OutcomeMonitoringRequest(BaseModel):
    packet: Dict[str, Any] = Field(default_factory=dict)
    monitoring: Dict[str, Any] = Field(default_factory=dict)
    action: str = "evaluate"
    actor: str = ""
    actorRole: str = ""
    observation: Dict[str, Any] = Field(default_factory=dict)
    reassessment: Dict[str, Any] = Field(default_factory=dict)
    amendment: Dict[str, Any] = Field(default_factory=dict)
    notes: str = ""


def outcome_monitoring_template() -> Dict[str, Any]:
    return {
        "schema": OUTCOME_MONITORING_SCHEMA,
        "monitoring_version": "1.0",
        "status": "planning",
        "decision_status": "not_implemented",
        "decision_owner": {},
        "implementation_owner": {},
        "commitments": [],
        "targets": [],
        "indicators": [],
        "site_intelligence_connections": [],
        "monitoring_schedule": {"cadence": "monthly", "next_review_at": "", "last_reviewed_at": ""},
        "implementation_milestones": [],
        "emerging_risks": [],
        "assumption_invalidations": [],
        "reassessment_triggers": [],
        "trigger_evaluations": [],
        "monitoring_events": [],
        "reassessment_history": [],
        "implementation_amendments": [],
        "post_implementation_reviews": [],
        "lessons_learned": [],
        "decision_registry_entry": {},
        "summary": {
            "target_count": 0,
            "targets_on_track": 0,
            "targets_at_risk": 0,
            "targets_off_track": 0,
            "milestones_overdue": 0,
            "active_material_risks": 0,
            "invalidated_assumptions": 0,
            "triggered_reassessments": 0,
        },
        "boundaries": [
            "Monitoring records observed results and implementation evidence; it does not certify causality or performance.",
            "Lifecycle amendments, suspension, and retirement require accountable human authorization.",
            "Site Intelligence links provide evidence context; source methodology, freshness, and confidence remain visible.",
        ],
    }


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _number(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_date(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        raw = str(value).strip().replace("Z", "+00:00")
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _event_hash(event: Dict[str, Any]) -> str:
    payload = {k: v for k, v in event.items() if k != "event_hash"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _canonical_sha256(canonical_hash: Callable[[Dict[str, Any]], str], value: Dict[str, Any]) -> str:
    """Return one canonical ``sha256:`` prefix regardless of the injected hasher contract."""
    digest = str(canonical_hash(value))
    return digest if digest.startswith("sha256:") else "sha256:" + digest


def _append_event(monitoring: Dict[str, Any], event_type: str, actor: str, actor_role: str, payload: Dict[str, Any], now: str) -> Dict[str, Any]:
    events = monitoring.setdefault("monitoring_events", [])
    previous_hash = events[-1].get("event_hash", "") if events else ""
    event = {
        "sequence": len(events) + 1,
        "event_type": event_type,
        "at": now,
        "actor": actor or "unspecified human actor",
        "actor_role": actor_role or "unspecified",
        "previous_event_hash": previous_hash,
        "payload": deepcopy(payload),
    }
    event["event_hash"] = _event_hash(event)
    events.append(event)
    return event


def _latest_actual(indicator: Dict[str, Any]) -> Optional[float]:
    observations = _as_list(indicator.get("observations"))
    for row in reversed(observations):
        if isinstance(row, dict):
            value = _number(row.get("value"))
            if value is not None:
                return value
    return _number(indicator.get("actual_value"))


def _evaluate_indicator(indicator: Dict[str, Any]) -> Dict[str, Any]:
    row = deepcopy(indicator)
    baseline = _number(row.get("baseline_value"))
    target = _number(row.get("target_value"))
    actual = _latest_actual(row)
    direction = str(row.get("direction") or "increase").strip().lower()
    tolerance = abs(_number(row.get("tolerance_percent")) or 10.0)
    status = "no_data"
    progress = None
    variance = None
    if actual is not None and target is not None:
        variance = actual - target
        if direction in {"decrease", "lower_is_better", "below"}:
            threshold = target * (1 + tolerance / 100) if target != 0 else tolerance / 100
            status = "on_track" if actual <= target else ("at_risk" if actual <= threshold else "off_track")
            if baseline is not None and baseline != target:
                progress = (baseline - actual) / (baseline - target) * 100
        elif direction in {"range", "within_range"}:
            low = _number(row.get("minimum_value"))
            high = _number(row.get("maximum_value"))
            if low is None: low = target * (1 - tolerance / 100)
            if high is None: high = target * (1 + tolerance / 100)
            status = "on_track" if low <= actual <= high else "off_track"
        else:
            threshold = target * (1 - tolerance / 100)
            status = "on_track" if actual >= target else ("at_risk" if actual >= threshold else "off_track")
            if baseline is not None and baseline != target:
                progress = (actual - baseline) / (target - baseline) * 100
    row.update({
        "actual_value": actual,
        "status": status,
        "variance_from_target": None if variance is None else round(variance, 6),
        "progress_percent": None if progress is None else round(max(-999.0, min(999.0, progress)), 2),
    })
    return row


def _milestone_status(milestone: Dict[str, Any], now_dt: datetime) -> Dict[str, Any]:
    row = deepcopy(milestone)
    status = str(row.get("status") or "not_started").lower()
    due = _parse_date(row.get("due_at"))
    completed = status in {"completed", "verified", "cancelled"}
    overdue = bool(due and due < now_dt and not completed)
    if overdue:
        status = "overdue"
    row["status"] = status
    row["overdue"] = overdue
    return row


def _risk_is_material(risk: Dict[str, Any]) -> bool:
    return str(risk.get("status") or "active").lower() not in {"closed", "resolved", "accepted"} and str(risk.get("severity") or "medium").lower() in {"high", "critical", "severe"}


def _evaluate_trigger(trigger: Dict[str, Any], monitoring: Dict[str, Any], now_dt: datetime) -> Dict[str, Any]:
    row = deepcopy(trigger)
    kind = str(row.get("type") or row.get("condition") or "manual").lower()
    triggered = bool(row.get("triggered", False))
    evidence: Dict[str, Any] = {}
    indicators = {str(i.get("indicator_id") or i.get("id")): i for i in monitoring.get("indicators", []) if isinstance(i, dict)}
    if kind in {"indicator_below", "threshold_below"}:
        indicator = indicators.get(str(row.get("indicator_id") or ""), {})
        actual = _number(indicator.get("actual_value")); threshold = _number(row.get("threshold"))
        triggered = actual is not None and threshold is not None and actual < threshold
        evidence = {"actual": actual, "threshold": threshold}
    elif kind in {"indicator_above", "threshold_above"}:
        indicator = indicators.get(str(row.get("indicator_id") or ""), {})
        actual = _number(indicator.get("actual_value")); threshold = _number(row.get("threshold"))
        triggered = actual is not None and threshold is not None and actual > threshold
        evidence = {"actual": actual, "threshold": threshold}
    elif kind == "overdue_milestone":
        overdue = [m.get("milestone_id") or m.get("id") for m in monitoring.get("implementation_milestones", []) if isinstance(m, dict) and m.get("overdue")]
        triggered = bool(overdue)
        evidence = {"overdue_milestones": overdue}
    elif kind == "assumption_invalidated":
        invalid = [a.get("assumption_id") or a.get("id") for a in monitoring.get("assumption_invalidations", []) if isinstance(a, dict) and str(a.get("status") or "invalidated").lower() in {"invalidated", "materially_changed"}]
        triggered = bool(invalid)
        evidence = {"invalidated_assumptions": invalid}
    elif kind in {"material_risk", "emerging_risk"}:
        risks = [r.get("risk_id") or r.get("id") for r in monitoring.get("emerging_risks", []) if isinstance(r, dict) and _risk_is_material(r)]
        triggered = bool(risks)
        evidence = {"material_risks": risks}
    elif kind in {"date_due", "scheduled_reassessment"}:
        due = _parse_date(row.get("due_at") or monitoring.get("monitoring_schedule", {}).get("next_review_at"))
        triggered = bool(due and due <= now_dt)
        evidence = {"due_at": due.isoformat() if due else ""}
    row.update({"triggered": triggered, "evaluated_at": now_dt.isoformat(), "evidence": evidence})
    return row


def _decision_registry_entry(packet: Dict[str, Any], monitoring: Dict[str, Any], app_version: str, now: str, canonical_hash: Callable[[Dict[str, Any]], str]) -> Dict[str, Any]:
    project = _as_dict(packet.get("project"))
    governance = _as_dict(packet.get("governance_center"))
    entry = {
        "schema": DECISION_REGISTRY_SCHEMA,
        "registry_version": app_version,
        "decision_packet_id": packet.get("decision_packet_id", "SCDS-DRAFT"),
        "title": project.get("project_name") or packet.get("title") or "Decision record",
        "decision_question": project.get("decision_question", ""),
        "governance_state": governance.get("current_state", "draft"),
        "lifecycle_status": monitoring.get("decision_status", "not_implemented"),
        "monitoring_status": monitoring.get("status", "planning"),
        "decision_owner": monitoring.get("decision_owner") or governance.get("decision_owner") or {},
        "implementation_owner": monitoring.get("implementation_owner") or {},
        "approved_at": governance.get("approved_at", ""),
        "implemented_at": monitoring.get("implemented_at", ""),
        "last_monitored_at": now,
        "next_reassessment_at": monitoring.get("monitoring_schedule", {}).get("next_review_at", ""),
        "target_summary": monitoring.get("summary", {}),
        "amendment_count": len(monitoring.get("implementation_amendments", [])),
        "reassessment_count": len(monitoring.get("reassessment_history", [])),
        "retired_at": monitoring.get("retired_at", ""),
    }
    entry["registry_hash"] = _canonical_sha256(canonical_hash, entry)
    return entry


def generate_outcome_monitoring(
    req: OutcomeMonitoringRequest,
    *,
    packet_template_factory: Callable[[], Dict[str, Any]],
    governance_template_factory: Callable[[], Dict[str, Any]],
    app_version: str,
    packet_schema: str,
    canonical_hash: Callable[[Dict[str, Any]], str],
    utc_now: Callable[[], str],
) -> Dict[str, Any]:
    packet = packet_template_factory()
    packet.update(deepcopy(req.packet or {}))
    monitoring = outcome_monitoring_template()
    existing = packet.get("outcome_monitoring") if isinstance(packet.get("outcome_monitoring"), dict) else {}
    monitoring.update(deepcopy(existing))
    monitoring.update(deepcopy(req.monitoring or {}))
    monitoring["schema"] = OUTCOME_MONITORING_SCHEMA
    monitoring["monitoring_version"] = app_version
    governance = packet.get("governance_center") if isinstance(packet.get("governance_center"), dict) else governance_template_factory()
    now = utc_now()
    now_dt = _parse_date(now) or datetime.now(timezone.utc)
    action = str(req.action or "evaluate").strip().lower().replace("-", "_")

    if action in {"record_observation", "observe"}:
        obs = deepcopy(req.observation or {})
        indicator_id = str(obs.get("indicator_id") or obs.get("id") or "").strip()
        if not indicator_id or _number(obs.get("value")) is None:
            return {"ok": False, "version": app_version, "error": "indicator_observation_required", "message": "Observation requires indicator_id and numeric value."}
        matched = False
        indicators = _as_list(monitoring.get("indicators"))
        for indicator in indicators:
            if isinstance(indicator, dict) and str(indicator.get("indicator_id") or indicator.get("id")) == indicator_id:
                indicator.setdefault("observations", []).append({
                    "observation_id": obs.get("observation_id") or f"OBS-{len(indicator.get('observations', []))+1:04d}",
                    "value": _number(obs.get("value")),
                    "observed_at": obs.get("observed_at") or now,
                    "source": obs.get("source") or "manual",
                    "source_url": obs.get("source_url", ""),
                    "methodology": obs.get("methodology", ""),
                    "confidence": obs.get("confidence", "not specified"),
                    "notes": obs.get("notes", ""),
                })
                matched = True
                break
        if not matched:
            indicators.append({
                "indicator_id": indicator_id,
                "label": obs.get("label") or indicator_id,
                "unit": obs.get("unit", ""),
                "direction": obs.get("direction", "increase"),
                "baseline_value": obs.get("baseline_value"),
                "target_value": obs.get("target_value"),
                "observations": [{"observation_id": "OBS-0001", "value": _number(obs.get("value")), "observed_at": obs.get("observed_at") or now, "source": obs.get("source") or "manual", "source_url": obs.get("source_url", ""), "methodology": obs.get("methodology", ""), "confidence": obs.get("confidence", "not specified"), "notes": obs.get("notes", "")}],
            })
        monitoring["indicators"] = indicators
        _append_event(monitoring, "observation_recorded", req.actor, req.actorRole, obs, now)

    elif action == "reassess":
        if not req.actor.strip():
            return {"ok": False, "version": app_version, "error": "human_actor_required", "message": "Reassessment requires a named human actor."}
        reassessment = deepcopy(req.reassessment or {})
        event = {
            "schema": REASSESSMENT_EVENT_SCHEMA,
            "reassessment_id": reassessment.get("reassessment_id") or f"REA-{len(monitoring.get('reassessment_history', []))+1:04d}",
            "performed_at": reassessment.get("performed_at") or now,
            "performed_by": req.actor,
            "actor_role": req.actorRole or "decision owner",
            "reason": reassessment.get("reason") or req.notes or "Scheduled or trigger-based reassessment",
            "findings": _as_list(reassessment.get("findings")),
            "evidence_reviewed": _as_list(reassessment.get("evidence_reviewed")),
            "recommendation": reassessment.get("recommendation") or "continue_with_monitoring",
            "recommended_lifecycle_status": reassessment.get("recommended_lifecycle_status") or monitoring.get("decision_status", "implemented"),
            "human_authorization_required": True,
        }
        event["event_hash"] = _canonical_sha256(canonical_hash, event)
        monitoring.setdefault("reassessment_history", []).append(event)
        monitoring["monitoring_schedule"] = _as_dict(monitoring.get("monitoring_schedule"))
        monitoring["monitoring_schedule"]["last_reviewed_at"] = event["performed_at"]
        if reassessment.get("next_review_at"):
            monitoring["monitoring_schedule"]["next_review_at"] = reassessment["next_review_at"]
        _append_event(monitoring, "decision_reassessed", req.actor, req.actorRole, event, now)

    elif action == "amend":
        if not req.actor.strip():
            return {"ok": False, "version": app_version, "error": "human_actor_required", "message": "Decision amendment requires a named human actor."}
        amendment = deepcopy(req.amendment or {})
        if not amendment.get("summary"):
            return {"ok": False, "version": app_version, "error": "amendment_summary_required", "message": "Decision amendment requires a summary."}
        amendment.update({
            "amendment_id": amendment.get("amendment_id") or f"AMD-{len(monitoring.get('implementation_amendments', []))+1:04d}",
            "authorized_at": amendment.get("authorized_at") or now,
            "authorized_by": req.actor,
            "actor_role": req.actorRole or "decision owner",
            "human_authorized": True,
        })
        amendment["amendment_hash"] = _canonical_sha256(canonical_hash, amendment)
        monitoring.setdefault("implementation_amendments", []).append(amendment)
        monitoring["decision_status"] = "amended"
        _append_event(monitoring, "decision_amended", req.actor, req.actorRole, amendment, now)

    elif action == "retire":
        if not req.actor.strip():
            return {"ok": False, "version": app_version, "error": "human_actor_required", "message": "Decision retirement requires a named human actor."}
        reason = str((req.reassessment or {}).get("reason") or req.notes or "").strip()
        if not reason:
            return {"ok": False, "version": app_version, "error": "retirement_reason_required", "message": "Decision retirement requires a reason."}
        monitoring["decision_status"] = "retired"
        monitoring["status"] = "closed"
        monitoring["retired_at"] = now
        monitoring["retirement"] = {"retired_at": now, "retired_by": req.actor, "actor_role": req.actorRole or "decision owner", "reason": reason, "human_authorized": True}
        _append_event(monitoring, "decision_retired", req.actor, req.actorRole, monitoring["retirement"], now)

    # Recalculate indicators, milestones, risks, invalidations, and triggers for every action.
    monitoring["indicators"] = [_evaluate_indicator(i) for i in _as_list(monitoring.get("indicators")) if isinstance(i, dict)]
    monitoring["implementation_milestones"] = [_milestone_status(m, now_dt) for m in _as_list(monitoring.get("implementation_milestones")) if isinstance(m, dict)]
    monitoring["emerging_risks"] = [deepcopy(r) for r in _as_list(monitoring.get("emerging_risks")) if isinstance(r, dict)]
    monitoring["assumption_invalidations"] = [deepcopy(a) for a in _as_list(monitoring.get("assumption_invalidations")) if isinstance(a, dict)]
    monitoring["trigger_evaluations"] = [_evaluate_trigger(t, monitoring, now_dt) for t in _as_list(monitoring.get("reassessment_triggers")) if isinstance(t, dict)]

    on_track = sum(i.get("status") == "on_track" for i in monitoring["indicators"])
    at_risk = sum(i.get("status") == "at_risk" for i in monitoring["indicators"])
    off_track = sum(i.get("status") == "off_track" for i in monitoring["indicators"])
    overdue = sum(bool(m.get("overdue")) for m in monitoring["implementation_milestones"])
    material_risks = sum(_risk_is_material(r) for r in monitoring["emerging_risks"])
    invalidated = sum(str(a.get("status") or "invalidated").lower() in {"invalidated", "materially_changed"} for a in monitoring["assumption_invalidations"])
    triggered = sum(bool(t.get("triggered")) for t in monitoring["trigger_evaluations"])
    summary = {
        "target_count": len(monitoring["indicators"]),
        "targets_on_track": on_track,
        "targets_at_risk": at_risk,
        "targets_off_track": off_track,
        "milestones_overdue": overdue,
        "active_material_risks": material_risks,
        "invalidated_assumptions": invalidated,
        "triggered_reassessments": triggered,
    }
    monitoring["summary"] = summary
    if monitoring.get("decision_status") == "retired":
        monitoring["status"] = "closed"
    elif triggered or off_track or invalidated or material_risks:
        monitoring["status"] = "reassessment_required"
    elif at_risk or overdue:
        monitoring["status"] = "watch"
    elif monitoring["indicators"]:
        monitoring["status"] = "on_track"
    else:
        monitoring["status"] = "planning"

    governance_state = str(governance.get("current_state") or "draft")
    monitoring["governance_alignment"] = {
        "governance_state": governance_state,
        "implementation_monitoring_authorized": governance_state in {"approved", "implemented", "retired"},
        "note": "Monitoring plans may be drafted at any stage; recorded implementation outcomes should follow human approval and implementation authorization.",
    }
    monitoring["last_evaluated_at"] = now
    monitoring["notes"] = req.notes or monitoring.get("notes", "")
    monitoring["content_hash"] = _canonical_sha256(canonical_hash, {k: v for k, v in monitoring.items() if k not in {"content_hash", "decision_registry_entry"}})
    monitoring["decision_registry_entry"] = _decision_registry_entry(packet, monitoring, app_version, now, canonical_hash)

    packet["packet_version"] = app_version
    packet["decision_packet_schema"] = packet_schema
    packet["outcome_monitoring_schema"] = OUTCOME_MONITORING_SCHEMA
    packet["reassessment_event_schema"] = REASSESSMENT_EVENT_SCHEMA
    packet["decision_registry_schema"] = DECISION_REGISTRY_SCHEMA
    packet["outcome_monitoring"] = monitoring
    packet["decision_registry_entry"] = monitoring["decision_registry_entry"]
    packet["reassessment_history"] = monitoring.get("reassessment_history", [])
    packet["implementation_amendments"] = monitoring.get("implementation_amendments", [])
    formats = packet.setdefault("export_center", {}).setdefault("available_formats", [])
    for fmt in ("outcome_monitoring_json", "decision_registry_json", "reassessment_history_json"):
        if fmt not in formats:
            formats.append(fmt)
    return {
        "ok": True,
        "version": app_version,
        "schema": OUTCOME_MONITORING_SCHEMA,
        "action": action,
        "outcome_monitoring": monitoring,
        "decision_registry_entry": monitoring["decision_registry_entry"],
        "decision_packet": packet,
        "requires_reassessment": monitoring["status"] == "reassessment_required",
    }
