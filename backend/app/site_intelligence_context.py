from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

SITE_CONTEXT_BUNDLE_SCHEMA = "scds-site-intelligence-context-bundle/1.0"
SITE_SIGNAL_SNAPSHOT_SCHEMA = "scds-site-intelligence-signal-snapshot/1.0"
SITE_CONTEXT_RECEIPT_SCHEMA = "scds-site-intelligence-context-receipt/1.0"

BOUNDARY = (
    "Site Intelligence owns observation and public-intelligence context. Decision Studio preserves source identity, "
    "geography, observation time, freshness, methodology, limitations, and provenance, but does not infer causality, "
    "scenario likelihood, approval, or recommendation from a signal."
)


class SiteIntelligenceContextRequest(BaseModel):
    packet: Dict[str, Any] = Field(default_factory=dict)
    decisionObject: Dict[str, Any] = Field(default_factory=dict)
    contextBundle: Dict[str, Any] = Field(default_factory=dict)
    signals: List[Dict[str, Any]] = Field(default_factory=list)
    sourceVersion: str = ""
    capturedAt: str = ""
    geography: Any = Field(default_factory=dict)
    scenarioRefs: List[str] = Field(default_factory=list)
    reviewState: str = "needs_review"
    provenance: List[Any] = Field(default_factory=list)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return deepcopy(value)
    if value in (None, "", {}):
        return []
    return [deepcopy(value)]


def _source(signal: Dict[str, Any]) -> Dict[str, Any]:
    src = signal.get("source") if isinstance(signal.get("source"), dict) else {}
    return {
        "name": str(signal.get("source_name") or src.get("name") or ""),
        "short_name": str(signal.get("source_short_name") or src.get("short_name") or ""),
        "url": str(signal.get("source_url") or src.get("url") or ""),
        "type": str(signal.get("source_type") or src.get("type") or "public-intelligence-source"),
    }


def _geography(signal: Dict[str, Any], fallback: Any) -> Any:
    value = signal.get("geography")
    if value not in (None, "", {}, []):
        return deepcopy(value)
    fields = {k: deepcopy(signal[k]) for k in ("country", "region", "place", "lat", "long", "geometry") if signal.get(k) not in (None, "")}
    return fields or deepcopy(fallback or {})


def _methodology(signal: Dict[str, Any]) -> Any:
    if signal.get("methodology") not in (None, "", [], {}):
        return deepcopy(signal.get("methodology"))
    if signal.get("methodology_notes") not in (None, ""):
        return str(signal.get("methodology_notes"))
    return []


def _freshness(signal: Dict[str, Any]) -> str:
    state = str(signal.get("freshness_state") or "").strip().lower()
    if state:
        return state
    status = str(signal.get("status") or "").strip().lower()
    if status in {"current", "live", "fresh", "stale", "expired", "cached"}:
        return status
    return "unknown"


def signal_snapshot(
    signal: Dict[str, Any],
    *,
    app_version: str,
    source_version: str = "",
    fallback_geography: Any = None,
    scenario_refs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    raw = deepcopy(signal or {})
    source = _source(raw)
    signal_id = str(raw.get("signal_id") or raw.get("id") or raw.get("indicator_id") or "")
    artifact_core = {
        "signal_id": signal_id,
        "raw_payload": raw,
    }
    snapshot_id = f"site-snapshot:{signal_id or _hash(artifact_core)[:12]}:{_hash(artifact_core)[:16]}"
    refs = list(dict.fromkeys([str(x) for x in (_list(raw.get("scenario_refs")) or list(scenario_refs or [])) if str(x)]))
    return {
        "schema": SITE_SIGNAL_SNAPSHOT_SCHEMA,
        "version": app_version,
        "snapshot_id": snapshot_id,
        "signal_id": signal_id,
        "category": str(raw.get("category") or raw.get("domain") or "unspecified"),
        "label": str(raw.get("label") or raw.get("title") or raw.get("indicator") or signal_id or "Site Intelligence signal"),
        "value": deepcopy(raw.get("value")),
        "unit": str(raw.get("unit") or ""),
        "severity": str(raw.get("severity") or "informational"),
        "source": source,
        "geography": _geography(raw, fallback_geography),
        "observed_at": str(raw.get("observed_at") or raw.get("period") or ""),
        "updated_at": str(raw.get("updated_at") or ""),
        "freshness_state": _freshness(raw),
        "methodology": _methodology(raw),
        "limitations": _list(raw.get("limitations") or raw.get("limitation")),
        "detail": str(raw.get("detail") or raw.get("description") or ""),
        "destination_url": str(raw.get("destination_url") or raw.get("href") or ""),
        "scenario_refs": refs,
        "source_product": {"product": "site-intelligence", "name": "Site Intelligence", "version": source_version, "role": "real_world_context"},
        "raw_payload": raw,
        "signal_fingerprint": _hash(raw),
        "boundary": "This snapshot preserves Site Intelligence context. It does not by itself establish causality, forecast probability, or recommend a decision.",
    }


def _diagnostics(snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
    ids = [str(x.get("signal_id") or "") for x in snapshots]
    duplicate_ids = sorted({x for x in ids if x and ids.count(x) > 1})
    missing_source = [x["snapshot_id"] for x in snapshots if not (x.get("source") or {}).get("name")]
    missing_geography = [x["snapshot_id"] for x in snapshots if x.get("geography") in (None, "", {}, [])]
    missing_observed = [x["snapshot_id"] for x in snapshots if not x.get("observed_at")]
    unknown_freshness = [x["snapshot_id"] for x in snapshots if x.get("freshness_state") in ("", "unknown")]
    stale = [x["snapshot_id"] for x in snapshots if x.get("freshness_state") in ("stale", "expired")]
    explicit_scenario_links = sum(len(x.get("scenario_refs") or []) for x in snapshots)
    return {
        "signal_count": len(snapshots),
        "source_identified_count": len(snapshots) - len(missing_source),
        "geography_identified_count": len(snapshots) - len(missing_geography),
        "observation_time_identified_count": len(snapshots) - len(missing_observed),
        "freshness_identified_count": len(snapshots) - len(unknown_freshness),
        "stale_or_expired_count": len(stale),
        "explicit_scenario_link_count": explicit_scenario_links,
        "duplicate_signal_ids": duplicate_ids,
        "missing_source_snapshot_ids": missing_source,
        "missing_geography_snapshot_ids": missing_geography,
        "missing_observation_time_snapshot_ids": missing_observed,
        "unknown_freshness_snapshot_ids": unknown_freshness,
        "stale_or_expired_snapshot_ids": stale,
    }


def context_contracts_template(app_version: str) -> Dict[str, Any]:
    return {
        "version": app_version,
        "context_bundle_schema": SITE_CONTEXT_BUNDLE_SCHEMA,
        "signal_snapshot_schema": SITE_SIGNAL_SNAPSHOT_SCHEMA,
        "context_receipt_schema": SITE_CONTEXT_RECEIPT_SCHEMA,
        "source_product": "site-intelligence",
        "boundary": BOUNDARY,
    }


def context_bundle_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": SITE_CONTEXT_BUNDLE_SCHEMA,
        "version": app_version,
        "bundle_id": "",
        "decision_id": "",
        "captured_at": "",
        "source": {"product": "site-intelligence", "name": "Site Intelligence", "version": "", "role": "real_world_context"},
        "review_state": "needs_review",
        "snapshots": [],
        "provenance": [],
        "diagnostics": _diagnostics([]),
        "bundle_fingerprint": "",
        "boundary": BOUNDARY,
    }


def build_context_bundle(
    *,
    decision_id: str,
    signals: List[Dict[str, Any]],
    app_version: str,
    source_version: str = "",
    captured_at: str = "",
    geography: Any = None,
    scenario_refs: Optional[List[str]] = None,
    review_state: str = "needs_review",
    provenance: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    snapshots = [
        signal_snapshot(
            s,
            app_version=app_version,
            source_version=source_version,
            fallback_geography=geography,
            scenario_refs=scenario_refs,
        )
        for s in list(signals or [])
        if isinstance(s, dict)
    ]
    captured = captured_at or _now()
    core = {
        "decision_id": decision_id,
        "captured_at": captured,
        "source_version": source_version,
        "snapshot_fingerprints": [s["signal_fingerprint"] for s in snapshots],
    }
    bundle = {
        "schema": SITE_CONTEXT_BUNDLE_SCHEMA,
        "version": app_version,
        "bundle_id": f"site-context:{_hash(core)[:20]}",
        "decision_id": decision_id,
        "captured_at": captured,
        "source": {"product": "site-intelligence", "name": "Site Intelligence", "version": source_version, "role": "real_world_context"},
        "review_state": review_state or "needs_review",
        "snapshots": snapshots,
        "provenance": deepcopy(provenance or []),
        "diagnostics": _diagnostics(snapshots),
        "boundary": BOUNDARY,
    }
    bundle["bundle_fingerprint"] = _hash({k: v for k, v in bundle.items() if k != "bundle_fingerprint"})
    return bundle


def validate_context_bundle(bundle: Dict[str, Any], *, app_version: str) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    b = bundle if isinstance(bundle, dict) else {}
    if b.get("schema") != SITE_CONTEXT_BUNDLE_SCHEMA:
        errors.append("context bundle schema is invalid")
    if ((b.get("source") or {}).get("product")) != "site-intelligence":
        errors.append("source.product must be site-intelligence")
    snapshots = b.get("snapshots") if isinstance(b.get("snapshots"), list) else []
    for idx, snap in enumerate(snapshots):
        if not isinstance(snap, dict):
            errors.append(f"snapshot {idx} must be an object")
            continue
        if snap.get("schema") != SITE_SIGNAL_SNAPSHOT_SCHEMA:
            errors.append(f"snapshot {idx} schema is invalid")
        expected = _hash(snap.get("raw_payload") or {})
        if snap.get("signal_fingerprint") != expected:
            errors.append(f"snapshot {idx} signal fingerprint does not match raw payload")
        if not (snap.get("source") or {}).get("name"):
            warnings.append(f"snapshot {idx} has no source name")
        if not snap.get("observed_at"):
            warnings.append(f"snapshot {idx} has no observation time")
        if snap.get("freshness_state") in ("", "unknown"):
            warnings.append(f"snapshot {idx} has unknown freshness")
    expected_bundle = _hash({k: v for k, v in b.items() if k != "bundle_fingerprint"})
    if b.get("bundle_fingerprint") != expected_bundle:
        errors.append("context bundle fingerprint does not match bundle contents")
    return {
        "valid": not errors,
        "schema": SITE_CONTEXT_BUNDLE_SCHEMA,
        "app_version": app_version,
        "errors": errors,
        "warnings": warnings,
        "diagnostics": _diagnostics([x for x in snapshots if isinstance(x, dict)]),
        "boundary": BOUNDARY,
    }


def context_receipt(bundle: Dict[str, Any], validation: Dict[str, Any], *, app_version: str) -> Dict[str, Any]:
    core = {
        "bundle_id": bundle.get("bundle_id", ""),
        "bundle_fingerprint": bundle.get("bundle_fingerprint", ""),
        "accepted": bool(validation.get("valid")),
        "errors": validation.get("errors") or [],
    }
    return {
        "schema": SITE_CONTEXT_RECEIPT_SCHEMA,
        "version": app_version,
        "receipt_id": f"site-context-receipt:{_hash(core)[:20]}",
        "created_at": _now(),
        "bundle_id": bundle.get("bundle_id", ""),
        "decision_id": bundle.get("decision_id", ""),
        "accepted": bool(validation.get("valid")),
        "validation": deepcopy(validation),
        "bundle_fingerprint": bundle.get("bundle_fingerprint", ""),
        "truth_verified": False,
        "causality_inferred": False,
        "recommendation_generated": False,
        "boundary": "Receipt confirms schema and fingerprint integrity only. It is not source verification, truth verification, causal inference, approval, or recommendation.",
    }


def attach_site_context(
    decision_object: Dict[str, Any],
    bundle: Dict[str, Any],
    receipt: Dict[str, Any],
    *,
    app_version: str,
) -> Dict[str, Any]:
    out = deepcopy(decision_object or {})
    out.setdefault("schema", "scds-decision-object/1.0")
    out.setdefault("decision_id", bundle.get("decision_id", ""))
    out.setdefault("site_intelligence_context_bundles", []).append(deepcopy(bundle))
    out.setdefault("site_intelligence_context_receipts", []).append(deepcopy(receipt))
    out.setdefault("real_world_context", [])
    out.setdefault("evidence", [])
    out.setdefault("links", [])
    provenance = out.setdefault("provenance", {})
    provenance.setdefault("records", [])
    for snap in bundle.get("snapshots") or []:
        contextual = {
            "context_id": snap.get("snapshot_id", ""),
            "source_product": "site-intelligence",
            "signal_id": snap.get("signal_id", ""),
            "label": snap.get("label", ""),
            "category": snap.get("category", ""),
            "value": deepcopy(snap.get("value")),
            "unit": snap.get("unit", ""),
            "source": deepcopy(snap.get("source") or {}),
            "geography": deepcopy(snap.get("geography")),
            "observed_at": snap.get("observed_at", ""),
            "updated_at": snap.get("updated_at", ""),
            "freshness_state": snap.get("freshness_state", "unknown"),
            "methodology": deepcopy(snap.get("methodology")),
            "limitations": deepcopy(snap.get("limitations") or []),
            "signal_fingerprint": snap.get("signal_fingerprint", ""),
            "scenario_refs": deepcopy(snap.get("scenario_refs") or []),
            "evidence_role": "contextual_evidence",
            "causal_claim": False,
            "recommendation_effect": "none",
        }
        out["real_world_context"].append(contextual)
        out["evidence"].append(deepcopy(contextual))
        for scenario_ref in snap.get("scenario_refs") or []:
            out["links"].append({
                "relationship": "explicit_site_context_for_scenario",
                "scenario_ref": scenario_ref,
                "context_id": snap.get("snapshot_id", ""),
                "signal_fingerprint": snap.get("signal_fingerprint", ""),
                "automatic_score_change": False,
            })
    out["links"].append({
        "relationship": "site_intelligence_context_bundle",
        "bundle_id": bundle.get("bundle_id", ""),
        "bundle_fingerprint": bundle.get("bundle_fingerprint", ""),
        "signal_count": len(bundle.get("snapshots") or []),
    })
    provenance["records"].append({
        "at": _now(),
        "action": "site_intelligence_context_attached",
        "source_product": "site-intelligence",
        "bundle_id": bundle.get("bundle_id", ""),
        "receipt_id": receipt.get("receipt_id", ""),
        "bundle_fingerprint": bundle.get("bundle_fingerprint", ""),
    })
    outcome = out.setdefault("outcome_review", {})
    if not isinstance(outcome, dict):
        outcome = {}
        out["outcome_review"] = outcome
    outcome.setdefault("site_intelligence_context_refs", []).append({
        "bundle_id": bundle.get("bundle_id", ""),
        "captured_at": bundle.get("captured_at", ""),
        "signal_count": len(bundle.get("snapshots") or []),
    })
    out["version"] = app_version
    return out
