from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, Field

from app.tradeoff_matrix import (
    TRADEOFF_MATRIX_SCHEMA,
    _float,
    _normalize_score,
)

UNCERTAINTY_REGISTER_SCHEMA = "scds-uncertainty-register/1.0"
SENSITIVITY_ANALYSIS_SCHEMA = "scds-sensitivity-analysis/1.0"
CONFIDENCE_ASSESSMENT_SCHEMA = "scds-confidence-assessment/1.0"


class UncertaintyConfidenceRequest(BaseModel):
    packet: Dict[str, Any] = Field(default_factory=dict)
    decisionObject: Dict[str, Any] = Field(default_factory=dict)
    tradeoffMatrix: Dict[str, Any] = Field(default_factory=dict)
    uncertaintyRegister: Dict[str, Any] = Field(default_factory=dict)
    sensitivityAnalysis: Dict[str, Any] = Field(default_factory=dict)
    confidenceAssessment: Dict[str, Any] = Field(default_factory=dict)
    uncertainties: List[Dict[str, Any]] = Field(default_factory=list)
    sensitivityConfig: Dict[str, Any] = Field(default_factory=dict)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _slug(value: Any, fallback: str) -> str:
    text = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value or "")).strip("-")
    text = "-".join(part for part in text.split("-") if part)
    return text[:80] or fallback


def uncertainty_register_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": UNCERTAINTY_REGISTER_SCHEMA,
        "version": app_version,
        "uncertainty_register_id": "",
        "decision_id": "",
        "created_at": "",
        "updated_at": "",
        "uncertainties": [],
        "diagnostics": {
            "record_count": 0,
            "bounded_count": 0,
            "reviewed_count": 0,
            "invalid_bound_ids": [],
            "unknown_target_ids": [],
            "characterization_coverage_percent": 0.0,
        },
        "provenance": {"created_by": "decision-studio", "records": []},
        "boundary": "Uncertainty records describe bounded assumptions and input variability. They do not convert uncertainty into certainty or certify a decision outcome.",
    }


def sensitivity_analysis_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": SENSITIVITY_ANALYSIS_SCHEMA,
        "version": app_version,
        "sensitivity_analysis_id": "",
        "decision_id": "",
        "matrix_id": "",
        "created_at": "",
        "baseline_scores": [],
        "criterion_weight_sensitivity": [],
        "evaluation_uncertainty_sensitivity": [],
        "alternative_score_envelopes": [],
        "pairwise_overlap_diagnostics": [],
        "diagnostics": {
            "weight_tests": 0,
            "uncertainty_tests": 0,
            "max_absolute_score_shift": 0.0,
            "ordering_reversal_observed": False,
        },
        "configuration": {"weight_perturbation_percent": 20.0},
        "boundary": "Sensitivity results show how comparative scores respond to explicit perturbations. They are not forecasts, probabilities, winner selection, or recommendations.",
    }


def confidence_assessment_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": CONFIDENCE_ASSESSMENT_SCHEMA,
        "version": app_version,
        "confidence_assessment_id": "",
        "decision_id": "",
        "matrix_id": "",
        "created_at": "",
        "dimensions": {
            "matrix_completeness_percent": 0.0,
            "review_coverage_percent": 0.0,
            "evidence_linkage_percent": 0.0,
            "uncertainty_characterization_percent": 0.0,
            "sensitivity_coverage_percent": 0.0,
        },
        "process_confidence_index": 0.0,
        "process_confidence_level": "insufficient",
        "limiting_factors": [],
        "interpretation": "",
        "boundary": "Process confidence describes documentation, review, evidence linkage, uncertainty characterization, and sensitivity coverage. It is not the probability that an alternative or recommendation is correct.",
    }


def _evaluation_ids(matrix: Dict[str, Any]) -> set[str]:
    return {str(x.get("evaluation_id")) for x in matrix.get("evaluations", []) if isinstance(x, dict) and x.get("evaluation_id")}


def _criterion_ids(matrix: Dict[str, Any]) -> set[str]:
    return {str(x.get("criterion_id")) for x in matrix.get("criteria_set", {}).get("criteria", []) if isinstance(x, dict) and x.get("criterion_id")}


def _alternative_ids(matrix: Dict[str, Any]) -> set[str]:
    return {str(x.get("alternative_id")) for x in matrix.get("alternatives_set", {}).get("alternatives", []) if isinstance(x, dict) and x.get("alternative_id")}


def normalize_uncertainty(record: Dict[str, Any], index: int, matrix: Dict[str, Any]) -> Dict[str, Any]:
    raw = deepcopy(record or {})
    uid = str(raw.get("uncertainty_id") or raw.get("id") or f"uncertainty-{index + 1}")
    target_type = str(raw.get("target_type") or raw.get("targetType") or "evaluation").strip().lower()
    if target_type not in {"evaluation", "criterion_weight", "criterion", "alternative", "assumption", "model", "scenario", "source", "decision"}:
        target_type = "decision"
    target_id = str(raw.get("target_id") or raw.get("targetId") or raw.get("evaluation_id") or raw.get("criterion_id") or "")
    method = str(raw.get("method") or raw.get("uncertainty_type") or "range").strip().lower()
    if method not in {"range", "interval", "distribution", "qualitative"}:
        method = "range"
    baseline = _float(raw.get("baseline"))
    lower = _float(raw.get("lower"))
    upper = _float(raw.get("upper"))
    if lower is None and isinstance(raw.get("range"), dict):
        lower = _float(raw["range"].get("min"))
    if upper is None and isinstance(raw.get("range"), dict):
        upper = _float(raw["range"].get("max"))
    if baseline is None and lower is not None and upper is not None:
        baseline = (lower + upper) / 2.0
    valid_bounds = lower is not None and upper is not None and lower <= upper
    target_known = True
    if target_type == "evaluation" and target_id:
        target_known = target_id in _evaluation_ids(matrix)
    elif target_type in {"criterion", "criterion_weight"} and target_id:
        target_known = target_id in _criterion_ids(matrix)
    elif target_type == "alternative" and target_id:
        target_known = target_id in _alternative_ids(matrix)
    return {
        "uncertainty_id": uid,
        "target_type": target_type,
        "target_id": target_id,
        "parameter": str(raw.get("parameter") or raw.get("field") or ("score" if target_type == "evaluation" else "value")),
        "label": str(raw.get("label") or raw.get("name") or uid),
        "method": method,
        "baseline": baseline,
        "lower": lower,
        "upper": upper,
        "unit": str(raw.get("unit") or ""),
        "distribution": deepcopy(raw.get("distribution") or {}),
        "confidence_level": _float(raw.get("confidence_level") or raw.get("confidenceLevel")),
        "source_refs": deepcopy(raw.get("source_refs") or raw.get("evidence_refs") or []),
        "rationale": str(raw.get("rationale") or raw.get("notes") or ""),
        "review_status": str(raw.get("review_status") or "needs_review"),
        "valid_bounds": valid_bounds,
        "target_known": target_known,
        "provenance": deepcopy(raw.get("provenance") or {}),
        "content_fingerprint": _fingerprint(raw),
        "raw": raw,
    }


def build_uncertainty_register(
    uncertainties: List[Dict[str, Any]],
    matrix: Dict[str, Any],
    app_version: str,
    decision_id: str = "",
) -> Dict[str, Any]:
    matrix = deepcopy(matrix or {})
    normalized = [normalize_uncertainty(item, i, matrix) for i, item in enumerate(uncertainties or []) if isinstance(item, dict)]
    unique: Dict[str, Dict[str, Any]] = {str(item["uncertainty_id"]): item for item in normalized}
    records = list(unique.values())
    bounded = [x for x in records if x.get("valid_bounds")]
    reviewed = [x for x in records if x.get("review_status") in {"reviewed", "accepted", "approved"}]
    invalid = [str(x.get("uncertainty_id")) for x in records if x.get("method") in {"range", "interval"} and not x.get("valid_bounds")]
    unknown = [str(x.get("uncertainty_id")) for x in records if not x.get("target_known")]
    coverage = round((len(bounded) / max(1, len(records))) * 100.0, 1) if records else 0.0
    now = _utc_now()
    fingerprint = _fingerprint([(x.get("uncertainty_id"), x.get("content_fingerprint")) for x in records])
    return {
        "schema": UNCERTAINTY_REGISTER_SCHEMA,
        "version": app_version,
        "uncertainty_register_id": f"uncertainty-register-{fingerprint[:16]}",
        "decision_id": decision_id,
        "created_at": now,
        "updated_at": now,
        "uncertainties": records,
        "diagnostics": {
            "record_count": len(records),
            "bounded_count": len(bounded),
            "reviewed_count": len(reviewed),
            "invalid_bound_ids": invalid,
            "unknown_target_ids": unknown,
            "characterization_coverage_percent": coverage,
        },
        "provenance": {"created_by": "decision-studio", "records": []},
        "boundary": "Uncertainty records describe bounded assumptions and input variability. They do not convert uncertainty into certainty or certify a decision outcome.",
    }


def _matrix_components(matrix: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    criteria = [deepcopy(x) for x in matrix.get("criteria_set", {}).get("criteria", []) if isinstance(x, dict)]
    alternatives = [deepcopy(x) for x in matrix.get("alternatives_set", {}).get("alternatives", []) if isinstance(x, dict)]
    evaluations = [deepcopy(x) for x in matrix.get("evaluations", []) if isinstance(x, dict)]
    return criteria, alternatives, evaluations


def _score_map(matrix: Dict[str, Any]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for item in matrix.get("alternative_summaries", []):
        if isinstance(item, dict) and item.get("weighted_score") is not None and item.get("alternative_id"):
            out[str(item["alternative_id"])] = float(item["weighted_score"])
    return out


def _compute_scores(criteria: List[Dict[str, Any]], alternatives: List[Dict[str, Any]], evaluations: List[Dict[str, Any]]) -> Dict[str, float | None]:
    weights = {str(c.get("criterion_id")): max(0.0, float(c.get("weight") or 0.0)) for c in criteria if c.get("criterion_id")}
    total = sum(weights.values())
    normalized = {cid: (weight / total if total > 0 else 0.0) for cid, weight in weights.items()}
    cells = {(str(e.get("alternative_id")), str(e.get("criterion_id"))): e for e in evaluations}
    scores: Dict[str, float | None] = {}
    for alt in alternatives:
        aid = str(alt.get("alternative_id") or "")
        weighted = 0.0
        used = 0.0
        complete = True
        for criterion in criteria:
            cid = str(criterion.get("criterion_id") or "")
            cell = cells.get((aid, cid))
            if not cell or cell.get("score") is None:
                complete = False
                continue
            weight = normalized.get(cid, 0.0)
            weighted += float(cell["score"]) * weight
            used += weight
        scores[aid] = round(weighted / used, 4) if complete and used > 0 else None
    return scores


def _rank_order(scores: Dict[str, float | None]) -> List[str]:
    return [aid for aid, score in sorted(scores.items(), key=lambda item: (item[1] is None, -(item[1] if item[1] is not None else -1e9), item[0])) if score is not None]


def _criterion_map(criteria: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(c.get("criterion_id")): c for c in criteria if c.get("criterion_id")}


def run_sensitivity_analysis(
    matrix: Dict[str, Any],
    uncertainty_register: Dict[str, Any],
    app_version: str,
    decision_id: str = "",
    config: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    matrix = deepcopy(matrix or {})
    if matrix.get("schema") != TRADEOFF_MATRIX_SCHEMA:
        template = sensitivity_analysis_template(app_version)
        template["diagnostics"]["error"] = "A scds-tradeoff-matrix/1.0 matrix is required."
        return template
    config = deepcopy(config or {})
    perturb_pct = _float(config.get("weight_perturbation_percent"), 20.0) or 20.0
    perturb_pct = min(max(perturb_pct, 0.0), 100.0)
    criteria, alternatives, evaluations = _matrix_components(matrix)
    baseline_scores = _compute_scores(criteria, alternatives, evaluations)
    baseline_order = _rank_order(baseline_scores)
    criterion_tests: List[Dict[str, Any]] = []
    uncertainty_tests: List[Dict[str, Any]] = []
    all_scenarios: List[Dict[str, float | None]] = [baseline_scores]
    ordering_reversal = False

    for criterion in criteria:
        cid = str(criterion.get("criterion_id") or "")
        original = float(criterion.get("weight") or 0.0)
        low_weight = max(0.0, original * (1.0 - perturb_pct / 100.0))
        high_weight = original * (1.0 + perturb_pct / 100.0)
        row = {"criterion_id": cid, "criterion_name": criterion.get("name", cid), "baseline_weight": original, "tests": []}
        for label, value in [("low", low_weight), ("high", high_weight)]:
            changed = deepcopy(criteria)
            for c in changed:
                if str(c.get("criterion_id")) == cid:
                    c["weight"] = value
            scores = _compute_scores(changed, alternatives, evaluations)
            all_scenarios.append(scores)
            order = _rank_order(scores)
            reversal = bool(baseline_order and order and order != baseline_order)
            ordering_reversal = ordering_reversal or reversal
            row["tests"].append({
                "case": label,
                "weight": round(value, 6),
                "alternative_scores": [{"alternative_id": aid, "score": score, "delta_from_baseline": round(score - baseline_scores[aid], 4) if score is not None and baseline_scores.get(aid) is not None else None} for aid, score in scores.items()],
                "ordering_changed": reversal,
            })
        criterion_tests.append(row)

    eval_map = {str(e.get("evaluation_id")): e for e in evaluations if e.get("evaluation_id")}
    criteria_by_id = _criterion_map(criteria)
    for uncertainty in uncertainty_register.get("uncertainties", []):
        if not isinstance(uncertainty, dict) or uncertainty.get("target_type") != "evaluation" or not uncertainty.get("valid_bounds"):
            continue
        eid = str(uncertainty.get("target_id") or "")
        original_cell = eval_map.get(eid)
        if not original_cell:
            continue
        cid = str(original_cell.get("criterion_id") or "")
        criterion = criteria_by_id.get(cid, {})
        parameter = str(uncertainty.get("parameter") or "score")
        row = {"uncertainty_id": uncertainty.get("uncertainty_id"), "evaluation_id": eid, "alternative_id": original_cell.get("alternative_id"), "criterion_id": cid, "parameter": parameter, "tests": []}
        for label, bound in [("lower", uncertainty.get("lower")), ("upper", uncertainty.get("upper"))]:
            changed = deepcopy(evaluations)
            for cell in changed:
                if str(cell.get("evaluation_id")) != eid:
                    continue
                if parameter in {"score", "normalized_score"}:
                    score = _float(bound)
                    cell["score"] = min(max(score, 0.0), 100.0) if score is not None else None
                else:
                    cell["value"] = bound
                    derived, _ = _normalize_score(bound, criterion)
                    cell["score"] = derived
            scores = _compute_scores(criteria, alternatives, changed)
            all_scenarios.append(scores)
            order = _rank_order(scores)
            reversal = bool(baseline_order and order and order != baseline_order)
            ordering_reversal = ordering_reversal or reversal
            row["tests"].append({
                "case": label,
                "input": bound,
                "alternative_scores": [{"alternative_id": aid, "score": score, "delta_from_baseline": round(score - baseline_scores[aid], 4) if score is not None and baseline_scores.get(aid) is not None else None} for aid, score in scores.items()],
                "ordering_changed": reversal,
            })
        uncertainty_tests.append(row)

    envelopes: List[Dict[str, Any]] = []
    max_shift = 0.0
    for alt in alternatives:
        aid = str(alt.get("alternative_id") or "")
        vals = [scores.get(aid) for scores in all_scenarios if scores.get(aid) is not None]
        if vals:
            low, high = min(vals), max(vals)
            base = baseline_scores.get(aid)
            if base is not None:
                max_shift = max(max_shift, abs(low - base), abs(high - base))
            envelopes.append({"alternative_id": aid, "name": alt.get("name", aid), "baseline_score": base, "min_score": round(low, 4), "max_score": round(high, 4), "span": round(high - low, 4)})
        else:
            envelopes.append({"alternative_id": aid, "name": alt.get("name", aid), "baseline_score": None, "min_score": None, "max_score": None, "span": None})

    overlaps: List[Dict[str, Any]] = []
    for i, left in enumerate(envelopes):
        for right in envelopes[i + 1:]:
            if left["min_score"] is None or right["min_score"] is None:
                continue
            overlap_low = max(left["min_score"], right["min_score"])
            overlap_high = min(left["max_score"], right["max_score"])
            overlaps.append({
                "alternative_a": left["alternative_id"],
                "alternative_b": right["alternative_id"],
                "score_ranges_overlap": overlap_low <= overlap_high,
                "overlap_interval": [round(overlap_low, 4), round(overlap_high, 4)] if overlap_low <= overlap_high else [],
            })

    now = _utc_now()
    payload_id = _fingerprint({"matrix_id": matrix.get("matrix_id"), "register_id": uncertainty_register.get("uncertainty_register_id"), "config": config})[:16]
    return {
        "schema": SENSITIVITY_ANALYSIS_SCHEMA,
        "version": app_version,
        "sensitivity_analysis_id": f"sensitivity-analysis-{payload_id}",
        "decision_id": decision_id or str(matrix.get("decision_id") or ""),
        "matrix_id": str(matrix.get("matrix_id") or ""),
        "created_at": now,
        "baseline_scores": [{"alternative_id": aid, "score": score} for aid, score in baseline_scores.items()],
        "criterion_weight_sensitivity": criterion_tests,
        "evaluation_uncertainty_sensitivity": uncertainty_tests,
        "alternative_score_envelopes": envelopes,
        "pairwise_overlap_diagnostics": overlaps,
        "diagnostics": {
            "weight_tests": sum(len(x.get("tests", [])) for x in criterion_tests),
            "uncertainty_tests": sum(len(x.get("tests", [])) for x in uncertainty_tests),
            "max_absolute_score_shift": round(max_shift, 4),
            "ordering_reversal_observed": ordering_reversal,
        },
        "configuration": {"weight_perturbation_percent": round(perturb_pct, 4)},
        "boundary": "Sensitivity results show how comparative scores respond to explicit perturbations. They are not forecasts, probabilities, winner selection, or recommendations.",
    }


def assess_confidence(
    matrix: Dict[str, Any],
    uncertainty_register: Dict[str, Any],
    sensitivity_analysis: Dict[str, Any],
    app_version: str,
    decision_id: str = "",
) -> Dict[str, Any]:
    evaluations = [x for x in matrix.get("evaluations", []) if isinstance(x, dict)]
    matrix_coverage = _float(matrix.get("diagnostics", {}).get("matrix_coverage_percent"), 0.0) or 0.0
    reviewed = [x for x in evaluations if x.get("review_status") in {"reviewed", "accepted", "approved"}]
    with_evidence = [x for x in evaluations if x.get("evidence_refs")]
    review_pct = round((len(reviewed) / max(1, len(evaluations))) * 100.0, 1) if evaluations else 0.0
    evidence_pct = round((len(with_evidence) / max(1, len(evaluations))) * 100.0, 1) if evaluations else 0.0
    uncertainty_pct = _float(uncertainty_register.get("diagnostics", {}).get("characterization_coverage_percent"), 0.0) or 0.0
    criteria_count = len(matrix.get("criteria_set", {}).get("criteria", []))
    uncertainty_count = int(sensitivity_analysis.get("diagnostics", {}).get("uncertainty_tests", 0) or 0)
    weight_tests = int(sensitivity_analysis.get("diagnostics", {}).get("weight_tests", 0) or 0)
    expected_weight_tests = criteria_count * 2
    sensitivity_pct = 0.0
    if expected_weight_tests or uncertainty_register.get("uncertainties"):
        covered = weight_tests + uncertainty_count
        expected = expected_weight_tests + 2 * len([x for x in uncertainty_register.get("uncertainties", []) if isinstance(x, dict) and x.get("target_type") == "evaluation" and x.get("valid_bounds")])
        sensitivity_pct = round((covered / max(1, expected)) * 100.0, 1)
    dimensions = {
        "matrix_completeness_percent": round(matrix_coverage, 1),
        "review_coverage_percent": review_pct,
        "evidence_linkage_percent": evidence_pct,
        "uncertainty_characterization_percent": round(uncertainty_pct, 1),
        "sensitivity_coverage_percent": sensitivity_pct,
    }
    index = round(sum(dimensions.values()) / len(dimensions), 1)
    floor = min(dimensions.values()) if dimensions else 0.0
    if index >= 90 and floor >= 80:
        level = "high_process_confidence"
    elif index >= 70 and floor >= 50:
        level = "moderate_process_confidence"
    elif index >= 50:
        level = "limited_process_confidence"
    else:
        level = "insufficient_process_confidence"
    limiting = [key for key, value in dimensions.items() if value < 70.0]
    if sensitivity_analysis.get("diagnostics", {}).get("ordering_reversal_observed"):
        limiting.append("ordering_changes_under_tested_perturbations")
    if matrix.get("diagnostics", {}).get("threshold_violations"):
        limiting.append("threshold_violations_present")
    interpretation = (
        f"{level.replace('_', ' ').capitalize()}: process confidence index {index}/100. "
        "This index summarizes documentation and analysis coverage only; it is not a probability of correctness."
    )
    now = _utc_now()
    fingerprint = _fingerprint({"matrix_id": matrix.get("matrix_id"), "register": uncertainty_register.get("uncertainty_register_id"), "sensitivity": sensitivity_analysis.get("sensitivity_analysis_id"), "dimensions": dimensions})[:16]
    return {
        "schema": CONFIDENCE_ASSESSMENT_SCHEMA,
        "version": app_version,
        "confidence_assessment_id": f"confidence-assessment-{fingerprint}",
        "decision_id": decision_id or str(matrix.get("decision_id") or ""),
        "matrix_id": str(matrix.get("matrix_id") or ""),
        "created_at": now,
        "dimensions": dimensions,
        "process_confidence_index": index,
        "process_confidence_level": level,
        "limiting_factors": sorted(set(limiting)),
        "interpretation": interpretation,
        "boundary": "Process confidence describes documentation, review, evidence linkage, uncertainty characterization, and sensitivity coverage. It is not the probability that an alternative or recommendation is correct.",
    }


def attach_uncertainty_confidence(
    decision_object: Dict[str, Any],
    register: Dict[str, Any],
    sensitivity: Dict[str, Any],
    confidence: Dict[str, Any],
    app_version: str,
) -> Dict[str, Any]:
    out = deepcopy(decision_object or {})
    out.setdefault("uncertainty_registers", [])
    out.setdefault("sensitivity_analyses", [])
    out.setdefault("confidence_assessments", [])
    out["uncertainty_registers"] = [x for x in out["uncertainty_registers"] if isinstance(x, dict) and x.get("uncertainty_register_id") != register.get("uncertainty_register_id")] + [deepcopy(register)]
    out["sensitivity_analyses"] = [x for x in out["sensitivity_analyses"] if isinstance(x, dict) and x.get("sensitivity_analysis_id") != sensitivity.get("sensitivity_analysis_id")] + [deepcopy(sensitivity)]
    out["confidence_assessments"] = [x for x in out["confidence_assessments"] if isinstance(x, dict) and x.get("confidence_assessment_id") != confidence.get("confidence_assessment_id")] + [deepcopy(confidence)]
    out["uncertainties"] = deepcopy(register.get("uncertainties", []))
    out["confidence"] = {
        "process_confidence_index": confidence.get("process_confidence_index"),
        "process_confidence_level": confidence.get("process_confidence_level"),
        "limiting_factors": deepcopy(confidence.get("limiting_factors", [])),
        "boundary": confidence.get("boundary"),
    }
    out.setdefault("provenance", {}).setdefault("records", []).append({
        "at": _utc_now(),
        "action": "uncertainty_sensitivity_confidence_attached",
        "uncertainty_register_id": register.get("uncertainty_register_id", ""),
        "sensitivity_analysis_id": sensitivity.get("sensitivity_analysis_id", ""),
        "confidence_assessment_id": confidence.get("confidence_assessment_id", ""),
    })
    out["updated_at"] = _utc_now()
    out["version"] = app_version
    return out
