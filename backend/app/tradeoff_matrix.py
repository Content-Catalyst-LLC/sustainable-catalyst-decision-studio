from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, Field

CRITERIA_SET_SCHEMA = "scds-criteria-set/1.0"
ALTERNATIVES_SET_SCHEMA = "scds-alternatives-set/1.0"
TRADEOFF_MATRIX_SCHEMA = "scds-tradeoff-matrix/1.0"
TRADEOFF_DIAGNOSTICS_SCHEMA = "scds-tradeoff-diagnostics/1.0"


class TradeoffMatrixRequest(BaseModel):
    packet: Dict[str, Any] = Field(default_factory=dict)
    decisionObject: Dict[str, Any] = Field(default_factory=dict)
    criteriaSet: Dict[str, Any] = Field(default_factory=dict)
    alternativesSet: Dict[str, Any] = Field(default_factory=dict)
    tradeoffMatrix: Dict[str, Any] = Field(default_factory=dict)
    criteria: List[Dict[str, Any]] = Field(default_factory=list)
    alternatives: List[Dict[str, Any]] = Field(default_factory=list)
    evaluations: List[Dict[str, Any]] = Field(default_factory=list)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _slug(value: Any, fallback: str) -> str:
    text = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value or "")).strip("-")
    text = "-".join(part for part in text.split("-") if part)
    return text[:80] or fallback


def _criterion_id(record: Dict[str, Any], index: int) -> str:
    explicit = record.get("criterion_id") or record.get("id")
    if explicit:
        return str(explicit)
    name = record.get("name") or record.get("label") or record.get("criterion") or f"criterion-{index + 1}"
    return f"criterion-{_slug(name, str(index + 1))}"


def _alternative_id(record: Dict[str, Any], index: int) -> str:
    explicit = record.get("alternative_id") or record.get("id")
    if explicit:
        return str(explicit)
    name = record.get("name") or record.get("label") or record.get("title") or f"alternative-{index + 1}"
    return f"alternative-{_slug(name, str(index + 1))}"


def _float(value: Any, default: float | None = None) -> float | None:
    if isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def criteria_set_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": CRITERIA_SET_SCHEMA,
        "version": app_version,
        "criteria_set_id": "",
        "title": "",
        "created_at": "",
        "updated_at": "",
        "criteria": [],
        "weighting": {"input_weight_total": 0.0, "normalized": False},
        "provenance": {"created_by": "decision-studio", "records": []},
        "boundary": "Criteria and weights make judgment explicit. They do not establish objective importance or authorize a decision.",
    }


def alternatives_set_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": ALTERNATIVES_SET_SCHEMA,
        "version": app_version,
        "alternatives_set_id": "",
        "title": "",
        "created_at": "",
        "updated_at": "",
        "alternatives": [],
        "provenance": {"created_by": "decision-studio", "records": []},
        "boundary": "Alternatives are candidate choices. Inclusion, omission, or ordering does not imply endorsement.",
    }


def tradeoff_matrix_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": TRADEOFF_MATRIX_SCHEMA,
        "version": app_version,
        "matrix_id": "",
        "decision_id": "",
        "title": "",
        "created_at": "",
        "updated_at": "",
        "criteria_set": criteria_set_template(app_version),
        "alternatives_set": alternatives_set_template(app_version),
        "evaluations": [],
        "alternative_summaries": [],
        "diagnostics": tradeoff_diagnostics([], [], [], app_version),
        "provenance": {"created_by": "decision-studio", "records": []},
        "review": {"status": "needs_review", "reviewed_by": "", "reviewed_at": ""},
        "boundary": "Weighted scores support comparison only. Decision Studio does not automatically select a winner, recommend an alternative, or replace accountable human judgment.",
    }


def normalize_criterion(record: Dict[str, Any], index: int) -> Dict[str, Any]:
    raw = deepcopy(record or {})
    cid = _criterion_id(raw, index)
    weight = max(0.0, _float(raw.get("weight"), 0.0) or 0.0)
    direction = str(raw.get("direction") or raw.get("preference") or "maximize").lower()
    if direction not in {"maximize", "minimize", "target", "qualitative"}:
        direction = "maximize"
    scale = raw.get("scale") if isinstance(raw.get("scale"), dict) else {}
    threshold = raw.get("threshold")
    return {
        "criterion_id": cid,
        "name": str(raw.get("name") or raw.get("label") or raw.get("criterion") or cid),
        "description": str(raw.get("description") or ""),
        "category": str(raw.get("category") or raw.get("pillar") or "general"),
        "criterion_type": str(raw.get("criterion_type") or raw.get("type") or "benefit"),
        "weight": round(weight, 6),
        "normalized_weight": 0.0,
        "direction": direction,
        "scale": deepcopy(scale),
        "threshold": deepcopy(threshold),
        "required": bool(raw.get("required", False)),
        "evidence_refs": deepcopy(raw.get("evidence_refs") or raw.get("source_ids") or []),
        "provenance": deepcopy(raw.get("provenance") or {}),
        "content_fingerprint": _fingerprint(raw),
        "raw": raw,
    }


def build_criteria_set(criteria: List[Dict[str, Any]], app_version: str, title: str = "") -> Dict[str, Any]:
    normalized = [normalize_criterion(item, i) for i, item in enumerate(criteria or []) if isinstance(item, dict)]
    unique: Dict[str, Dict[str, Any]] = {}
    for item in normalized:
        unique[item["criterion_id"]] = item
    records = list(unique.values())
    weight_total = sum(float(item.get("weight") or 0.0) for item in records)
    for item in records:
        item["normalized_weight"] = round((float(item.get("weight") or 0.0) / weight_total), 8) if weight_total > 0 else 0.0
    now = _utc_now()
    return {
        "schema": CRITERIA_SET_SCHEMA,
        "version": app_version,
        "criteria_set_id": f"criteria-set-{_fingerprint([(x['criterion_id'], x['content_fingerprint']) for x in records])[:16]}",
        "title": title or "Decision criteria set",
        "created_at": now,
        "updated_at": now,
        "criteria": records,
        "weighting": {"input_weight_total": round(weight_total, 6), "normalized": weight_total > 0},
        "provenance": {"created_by": "decision-studio", "records": []},
        "boundary": "Criteria and weights make judgment explicit. They do not establish objective importance or authorize a decision.",
    }


def normalize_alternative(record: Dict[str, Any], index: int) -> Dict[str, Any]:
    raw = deepcopy(record or {})
    aid = _alternative_id(raw, index)
    return {
        "alternative_id": aid,
        "name": str(raw.get("name") or raw.get("label") or raw.get("title") or aid),
        "description": str(raw.get("description") or raw.get("summary") or ""),
        "status": str(raw.get("status") or "candidate"),
        "attributes": deepcopy(raw.get("attributes") or {}),
        "constraints": deepcopy(raw.get("constraints") or []),
        "evidence_refs": deepcopy(raw.get("evidence_refs") or raw.get("source_ids") or []),
        "provenance": deepcopy(raw.get("provenance") or {}),
        "content_fingerprint": _fingerprint(raw),
        "raw": raw,
    }


def build_alternatives_set(alternatives: List[Dict[str, Any]], app_version: str, title: str = "") -> Dict[str, Any]:
    normalized = [normalize_alternative(item, i) for i, item in enumerate(alternatives or []) if isinstance(item, dict)]
    unique: Dict[str, Dict[str, Any]] = {}
    for item in normalized:
        unique[item["alternative_id"]] = item
    records = list(unique.values())
    now = _utc_now()
    return {
        "schema": ALTERNATIVES_SET_SCHEMA,
        "version": app_version,
        "alternatives_set_id": f"alternatives-set-{_fingerprint([(x['alternative_id'], x['content_fingerprint']) for x in records])[:16]}",
        "title": title or "Decision alternatives set",
        "created_at": now,
        "updated_at": now,
        "alternatives": records,
        "provenance": {"created_by": "decision-studio", "records": []},
        "boundary": "Alternatives are candidate choices. Inclusion, omission, or ordering does not imply endorsement.",
    }


def _normalize_score(value: Any, criterion: Dict[str, Any]) -> Tuple[float | None, str]:
    direct = _float(value)
    if direct is None:
        return None, "missing"
    scale = criterion.get("scale") if isinstance(criterion.get("scale"), dict) else {}
    low = _float(scale.get("min"))
    high = _float(scale.get("max"))
    direction = criterion.get("direction") or "maximize"
    if low is not None and high is not None and high > low:
        bounded = min(max(direct, low), high)
        score = (bounded - low) / (high - low) * 100.0
        if direction == "minimize":
            score = 100.0 - score
        return round(score, 4), "derived_from_scale"
    if 0.0 <= direct <= 100.0:
        return round(direct, 4), "direct_0_100"
    return None, "unscored_value"


def normalize_evaluation(record: Dict[str, Any], criterion_map: Dict[str, Dict[str, Any]], alternative_map: Dict[str, Dict[str, Any]], index: int) -> Dict[str, Any]:
    raw = deepcopy(record or {})
    cid = str(raw.get("criterion_id") or raw.get("criterion") or "")
    aid = str(raw.get("alternative_id") or raw.get("alternative") or "")
    criterion = criterion_map.get(cid, {})
    explicit_score = raw.get("score") if "score" in raw else raw.get("normalized_score")
    if explicit_score is not None:
        score = _float(explicit_score)
        score = min(max(score, 0.0), 100.0) if score is not None else None
        score_source = "explicit"
    else:
        score, score_source = _normalize_score(raw.get("value"), criterion)
    threshold = criterion.get("threshold")
    threshold_violation = False
    if isinstance(threshold, dict):
        threshold_value = _float(threshold.get("value"))
        observed = _float(raw.get("value"))
        if threshold_value is not None and observed is not None:
            op = str(threshold.get("operator") or (">=" if criterion.get("direction") != "minimize" else "<="))
            if op == ">=":
                threshold_violation = observed < threshold_value
            elif op == ">":
                threshold_violation = observed <= threshold_value
            elif op == "<=":
                threshold_violation = observed > threshold_value
            elif op == "<":
                threshold_violation = observed >= threshold_value
            elif op == "==":
                threshold_violation = observed != threshold_value
    return {
        "evaluation_id": str(raw.get("evaluation_id") or raw.get("id") or f"evaluation-{index + 1}"),
        "alternative_id": aid,
        "criterion_id": cid,
        "value": deepcopy(raw.get("value")),
        "unit": str(raw.get("unit") or ""),
        "score": round(score, 4) if score is not None else None,
        "score_source": score_source,
        "evidence_refs": deepcopy(raw.get("evidence_refs") or raw.get("source_ids") or []),
        "confidence": deepcopy(raw.get("confidence") or {}),
        "notes": str(raw.get("notes") or ""),
        "review_status": str(raw.get("review_status") or "needs_review"),
        "threshold_violation": threshold_violation,
        "unknown_criterion": cid not in criterion_map,
        "unknown_alternative": aid not in alternative_map,
        "content_fingerprint": _fingerprint(raw),
        "raw": raw,
    }


def tradeoff_diagnostics(criteria: List[Dict[str, Any]], alternatives: List[Dict[str, Any]], evaluations: List[Dict[str, Any]], app_version: str) -> Dict[str, Any]:
    criterion_ids = [str(x.get("criterion_id")) for x in criteria if x.get("criterion_id")]
    alternative_ids = [str(x.get("alternative_id")) for x in alternatives if x.get("alternative_id")]
    present = {(str(x.get("alternative_id")), str(x.get("criterion_id"))) for x in evaluations if not x.get("unknown_criterion") and not x.get("unknown_alternative")}
    expected = {(a, c) for a in alternative_ids for c in criterion_ids}
    missing = [{"alternative_id": a, "criterion_id": c} for a, c in sorted(expected - present)]
    unknown_criteria = sorted({str(x.get("criterion_id")) for x in evaluations if x.get("unknown_criterion") and x.get("criterion_id")})
    unknown_alternatives = sorted({str(x.get("alternative_id")) for x in evaluations if x.get("unknown_alternative") and x.get("alternative_id")})
    unscored = [str(x.get("evaluation_id")) for x in evaluations if x.get("score") is None]
    needs_review = [str(x.get("evaluation_id")) for x in evaluations if x.get("review_status") not in {"reviewed", "accepted", "approved"}]
    threshold_violations = [
        {"evaluation_id": x.get("evaluation_id"), "alternative_id": x.get("alternative_id"), "criterion_id": x.get("criterion_id")}
        for x in evaluations if x.get("threshold_violation")
    ]
    weight_total = round(sum(float(x.get("weight") or 0.0) for x in criteria), 6)
    coverage = round((len(present) / max(1, len(expected))) * 100.0, 1)
    return {
        "schema": TRADEOFF_DIAGNOSTICS_SCHEMA,
        "version": app_version,
        "criteria_count": len(criteria),
        "alternatives_count": len(alternatives),
        "expected_cell_count": len(expected),
        "evaluated_cell_count": len(present),
        "matrix_coverage_percent": coverage,
        "input_weight_total": weight_total,
        "weights_normalizable": weight_total > 0,
        "missing_evaluations": missing,
        "unknown_criterion_ids": unknown_criteria,
        "unknown_alternative_ids": unknown_alternatives,
        "unscored_evaluation_ids": unscored,
        "needs_review_evaluation_ids": needs_review,
        "threshold_violations": threshold_violations,
        "complete": bool(criteria and alternatives) and not missing and not unknown_criteria and not unknown_alternatives and not unscored,
    }


def build_tradeoff_matrix(
    criteria: List[Dict[str, Any]],
    alternatives: List[Dict[str, Any]],
    evaluations: List[Dict[str, Any]],
    app_version: str,
    decision_id: str = "",
    criteria_set: Dict[str, Any] | None = None,
    alternatives_set: Dict[str, Any] | None = None,
    title: str = "",
) -> Dict[str, Any]:
    criteria_set = deepcopy(criteria_set or {})
    alternatives_set = deepcopy(alternatives_set or {})
    if criteria_set.get("schema") != CRITERIA_SET_SCHEMA:
        criteria_set = build_criteria_set(criteria, app_version)
    if alternatives_set.get("schema") != ALTERNATIVES_SET_SCHEMA:
        alternatives_set = build_alternatives_set(alternatives, app_version)
    criterion_records = [x for x in criteria_set.get("criteria", []) if isinstance(x, dict)]
    alternative_records = [x for x in alternatives_set.get("alternatives", []) if isinstance(x, dict)]
    criterion_map = {str(x.get("criterion_id")): x for x in criterion_records}
    alternative_map = {str(x.get("alternative_id")): x for x in alternative_records}
    normalized_evaluations = [normalize_evaluation(item, criterion_map, alternative_map, i) for i, item in enumerate(evaluations or []) if isinstance(item, dict)]
    diagnostics = tradeoff_diagnostics(criterion_records, alternative_records, normalized_evaluations, app_version)

    cell_map = {(str(x.get("alternative_id")), str(x.get("criterion_id"))): x for x in normalized_evaluations}
    summaries: List[Dict[str, Any]] = []
    for alt in alternative_records:
        aid = str(alt.get("alternative_id"))
        weighted_sum = 0.0
        weight_used = 0.0
        complete = True
        threshold_violations: List[str] = []
        for criterion in criterion_records:
            cid = str(criterion.get("criterion_id"))
            cell = cell_map.get((aid, cid))
            if not cell or cell.get("score") is None:
                complete = False
                continue
            weight = float(criterion.get("normalized_weight") or 0.0)
            weighted_sum += float(cell["score"]) * weight
            weight_used += weight
            if cell.get("threshold_violation"):
                threshold_violations.append(cid)
        score = round(weighted_sum / weight_used, 4) if weight_used > 0 and complete else None
        summaries.append({
            "alternative_id": aid,
            "name": alt.get("name", aid),
            "weighted_score": score,
            "complete": complete,
            "threshold_violation_criteria": threshold_violations,
            "score_interpretation": "Comparative decision-support score only; not an automatic recommendation.",
        })
    now = _utc_now()
    matrix_fingerprint = _fingerprint({
        "criteria_set_id": criteria_set.get("criteria_set_id"),
        "alternatives_set_id": alternatives_set.get("alternatives_set_id"),
        "evaluations": [x.get("content_fingerprint") for x in normalized_evaluations],
    })
    return {
        "schema": TRADEOFF_MATRIX_SCHEMA,
        "version": app_version,
        "matrix_id": f"tradeoff-matrix-{matrix_fingerprint[:16]}",
        "decision_id": decision_id,
        "title": title or "Decision tradeoff matrix",
        "created_at": now,
        "updated_at": now,
        "criteria_set": criteria_set,
        "alternatives_set": alternatives_set,
        "evaluations": normalized_evaluations,
        "alternative_summaries": summaries,
        "diagnostics": diagnostics,
        "provenance": {"created_by": "decision-studio", "records": []},
        "review": {"status": "needs_review", "reviewed_by": "", "reviewed_at": ""},
        "boundary": "Weighted scores support comparison only. Decision Studio does not automatically select a winner, recommend an alternative, or replace accountable human judgment.",
    }


def attach_tradeoff_matrix(decision_object: Dict[str, Any], matrix: Dict[str, Any], app_version: str) -> Dict[str, Any]:
    out = deepcopy(decision_object or {})
    out.setdefault("tradeoff_matrices", [])
    existing = [x for x in out["tradeoff_matrices"] if isinstance(x, dict) and x.get("matrix_id") != matrix.get("matrix_id")]
    out["tradeoff_matrices"] = existing + [deepcopy(matrix)]
    out["criteria"] = deepcopy(matrix.get("criteria_set", {}).get("criteria", []))
    out["alternatives"] = deepcopy(matrix.get("alternatives_set", {}).get("alternatives", []))
    out["tradeoffs"] = deepcopy(matrix.get("evaluations", []))
    out.setdefault("provenance", {}).setdefault("records", []).append({
        "at": _utc_now(),
        "action": "tradeoff_matrix_attached",
        "matrix_id": matrix.get("matrix_id", ""),
        "schema": TRADEOFF_MATRIX_SCHEMA,
    })
    out["updated_at"] = _utc_now()
    out["version"] = app_version
    return out
