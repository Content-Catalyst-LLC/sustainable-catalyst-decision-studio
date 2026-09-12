from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from app.tradeoff_matrix import TRADEOFF_MATRIX_SCHEMA, build_tradeoff_matrix
from app.uncertainty_confidence import CONFIDENCE_ASSESSMENT_SCHEMA

SCENARIO_SET_SCHEMA = "scds-scenario-set/1.0"
SCENARIO_COMPARISON_SCHEMA = "scds-scenario-comparison/1.0"
STRESS_TEST_SUITE_SCHEMA = "scds-stress-test-suite/1.0"


class ScenarioStressRequest(BaseModel):
    packet: Dict[str, Any] = Field(default_factory=dict)
    decisionObject: Dict[str, Any] = Field(default_factory=dict)
    tradeoffMatrix: Dict[str, Any] = Field(default_factory=dict)
    confidenceAssessment: Dict[str, Any] = Field(default_factory=dict)
    scenarioSet: Dict[str, Any] = Field(default_factory=dict)
    scenarioComparison: Dict[str, Any] = Field(default_factory=dict)
    stressTestSuite: Dict[str, Any] = Field(default_factory=dict)
    scenarios: List[Dict[str, Any]] = Field(default_factory=list)
    stressConfig: Dict[str, Any] = Field(default_factory=dict)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _slug(value: Any, fallback: str) -> str:
    text = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value or "")).strip("-")
    text = "-".join(part for part in text.split("-") if part)
    return text[:80] or fallback


def scenario_set_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": SCENARIO_SET_SCHEMA,
        "version": app_version,
        "scenario_set_id": "",
        "decision_id": "",
        "created_at": "",
        "updated_at": "",
        "scenarios": [],
        "diagnostics": {
            "scenario_count": 0,
            "baseline_count": 0,
            "stress_scenario_count": 0,
            "duplicate_ids": [],
            "unknown_criterion_refs": [],
            "unknown_evaluation_refs": [],
            "reviewed_count": 0,
        },
        "provenance": {"created_by": "decision-studio", "records": []},
        "boundary": "Scenarios are explicit decision conditions, not forecasts or probabilities. Scenario inclusion does not imply likelihood or endorsement.",
    }


def scenario_comparison_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": SCENARIO_COMPARISON_SCHEMA,
        "version": app_version,
        "scenario_comparison_id": "",
        "decision_id": "",
        "matrix_id": "",
        "created_at": "",
        "baseline_scenario_id": "",
        "scenario_results": [],
        "alternative_score_ranges": [],
        "diagnostics": {
            "scenario_count": 0,
            "complete_scenario_count": 0,
            "ordering_change_scenario_ids": [],
            "threshold_breach_scenario_ids": [],
            "incomplete_scenario_ids": [],
            "max_score_swing": 0.0,
        },
        "boundary": "Scenario comparison exposes conditional performance and instability. It does not predict which scenario will occur, choose a winner, or create a recommendation.",
    }


def stress_test_suite_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": STRESS_TEST_SUITE_SCHEMA,
        "version": app_version,
        "stress_test_suite_id": "",
        "decision_id": "",
        "created_at": "",
        "tests": [],
        "failure_modes": [],
        "diagnostics": {
            "test_count": 0,
            "passed_count": 0,
            "failed_count": 0,
            "stress_scenario_count": 0,
            "ordering_change_count": 0,
            "threshold_breach_count": 0,
        },
        "configuration": {
            "max_allowed_score_drop": 15.0,
            "max_allowed_threshold_violations": 0,
            "require_complete_matrix": True,
            "minimum_process_confidence": 0.0,
        },
        "boundary": "Stress tests identify conditions under which the comparison becomes fragile, incomplete, or constraint-violating. Passing a stress test is not approval, certification, or a recommendation.",
    }


def _matrix_ids(matrix: Dict[str, Any]) -> tuple[set[str], set[str]]:
    criteria = {
        str(x.get("criterion_id"))
        for x in matrix.get("criteria_set", {}).get("criteria", [])
        if isinstance(x, dict) and x.get("criterion_id")
    }
    evaluations = {
        str(x.get("evaluation_id"))
        for x in matrix.get("evaluations", [])
        if isinstance(x, dict) and x.get("evaluation_id")
    }
    return criteria, evaluations


def normalize_scenario(record: Dict[str, Any], index: int, matrix: Dict[str, Any]) -> Dict[str, Any]:
    raw = deepcopy(record or {})
    sid = str(raw.get("scenario_id") or raw.get("id") or _slug(raw.get("name") or raw.get("label"), f"scenario-{index+1}"))
    name = str(raw.get("name") or raw.get("label") or sid)
    kind = str(raw.get("kind") or raw.get("type") or ("baseline" if index == 0 else "custom")).strip().lower()
    if kind not in {"baseline", "expected", "upside", "downside", "stress", "custom"}:
        kind = "custom"
    weight_overrides = [deepcopy(x) for x in (raw.get("weight_overrides") or raw.get("criterion_weight_overrides") or []) if isinstance(x, dict)]
    evaluation_overrides = [deepcopy(x) for x in (raw.get("evaluation_overrides") or []) if isinstance(x, dict)]
    criteria_ids, evaluation_ids = _matrix_ids(matrix)
    unknown_criteria = sorted({str(x.get("criterion_id")) for x in weight_overrides if x.get("criterion_id") and str(x.get("criterion_id")) not in criteria_ids})
    unknown_evaluations = sorted({str(x.get("evaluation_id")) for x in evaluation_overrides if x.get("evaluation_id") and str(x.get("evaluation_id")) not in evaluation_ids})
    return {
        "scenario_id": sid,
        "name": name,
        "description": str(raw.get("description") or raw.get("summary") or ""),
        "kind": kind,
        "assumption_changes": deepcopy(raw.get("assumption_changes") or raw.get("assumptions") or []),
        "weight_overrides": weight_overrides,
        "evaluation_overrides": evaluation_overrides,
        "constraints": deepcopy(raw.get("constraints") or []),
        "source_refs": deepcopy(raw.get("source_refs") or raw.get("evidence_refs") or []),
        "review_status": str(raw.get("review_status") or "needs_review"),
        "unknown_criterion_refs": unknown_criteria,
        "unknown_evaluation_refs": unknown_evaluations,
        "provenance": deepcopy(raw.get("provenance") or {}),
        "content_fingerprint": _fingerprint(raw),
        "raw": raw,
    }


def build_scenario_set(scenarios: List[Dict[str, Any]], matrix: Dict[str, Any], app_version: str, decision_id: str = "") -> Dict[str, Any]:
    records = [normalize_scenario(item, i, matrix) for i, item in enumerate(scenarios or []) if isinstance(item, dict)]
    if not records:
        records = [normalize_scenario({"scenario_id": "baseline", "name": "Baseline", "kind": "baseline", "review_status": "reviewed"}, 0, matrix)]
    seen: set[str] = set()
    duplicate_ids: List[str] = []
    unique: Dict[str, Dict[str, Any]] = {}
    for item in records:
        sid = str(item["scenario_id"])
        if sid in seen:
            duplicate_ids.append(sid)
        seen.add(sid)
        unique[sid] = item
    records = list(unique.values())
    baseline_count = sum(1 for x in records if x.get("kind") == "baseline")
    stress_count = sum(1 for x in records if x.get("kind") == "stress")
    reviewed_count = sum(1 for x in records if x.get("review_status") in {"reviewed", "accepted", "approved"})
    unknown_criteria = sorted({ref for x in records for ref in x.get("unknown_criterion_refs", [])})
    unknown_evaluations = sorted({ref for x in records for ref in x.get("unknown_evaluation_refs", [])})
    now = _utc_now()
    fp = _fingerprint([(x["scenario_id"], x["content_fingerprint"]) for x in records])
    return {
        "schema": SCENARIO_SET_SCHEMA,
        "version": app_version,
        "scenario_set_id": f"scenario-set-{fp[:16]}",
        "decision_id": decision_id,
        "created_at": now,
        "updated_at": now,
        "scenarios": records,
        "diagnostics": {
            "scenario_count": len(records),
            "baseline_count": baseline_count,
            "stress_scenario_count": stress_count,
            "duplicate_ids": sorted(set(duplicate_ids)),
            "unknown_criterion_refs": unknown_criteria,
            "unknown_evaluation_refs": unknown_evaluations,
            "reviewed_count": reviewed_count,
        },
        "provenance": {"created_by": "decision-studio", "records": []},
        "boundary": "Scenarios are explicit decision conditions, not forecasts or probabilities. Scenario inclusion does not imply likelihood or endorsement.",
    }


def _scenario_matrix(matrix: Dict[str, Any], scenario: Dict[str, Any], app_version: str) -> Dict[str, Any]:
    criteria = []
    weight_map = {str(x.get("criterion_id")): x for x in scenario.get("weight_overrides", []) if isinstance(x, dict) and x.get("criterion_id")}
    for item in matrix.get("criteria_set", {}).get("criteria", []):
        if not isinstance(item, dict):
            continue
        raw = deepcopy(item.get("raw") or item)
        cid = str(item.get("criterion_id") or raw.get("criterion_id") or "")
        override = weight_map.get(cid)
        if override is not None and override.get("weight") is not None:
            raw["weight"] = override.get("weight")
        criteria.append(raw)
    alternatives = [deepcopy(x.get("raw") or x) for x in matrix.get("alternatives_set", {}).get("alternatives", []) if isinstance(x, dict)]
    eval_override_map = {str(x.get("evaluation_id")): x for x in scenario.get("evaluation_overrides", []) if isinstance(x, dict) and x.get("evaluation_id")}
    evaluations: List[Dict[str, Any]] = []
    for item in matrix.get("evaluations", []):
        if not isinstance(item, dict):
            continue
        raw = deepcopy(item.get("raw") or item)
        eid = str(item.get("evaluation_id") or raw.get("evaluation_id") or "")
        override = eval_override_map.get(eid)
        if override:
            if "value" in override and "score" not in override:
                raw.pop("score", None)
                raw.pop("normalized_score", None)
            for key in ("value", "score", "review_status", "evidence_refs"):
                if key in override:
                    raw[key] = deepcopy(override[key])
        evaluations.append(raw)
    return build_tradeoff_matrix(
        criteria,
        alternatives,
        evaluations,
        app_version,
        decision_id=str(matrix.get("decision_id") or ""),
        title=f"Scenario: {scenario.get('name') or scenario.get('scenario_id')}",
    )


def _order(matrix: Dict[str, Any]) -> List[str]:
    scored = [x for x in matrix.get("alternative_summaries", []) if isinstance(x, dict) and x.get("weighted_score") is not None]
    scored.sort(key=lambda x: (-float(x.get("weighted_score") or 0.0), str(x.get("alternative_id") or "")))
    return [str(x.get("alternative_id")) for x in scored]


def compare_scenarios(matrix: Dict[str, Any], scenario_set: Dict[str, Any], app_version: str, decision_id: str = "") -> Dict[str, Any]:
    scenarios = [x for x in scenario_set.get("scenarios", []) if isinstance(x, dict)]
    baseline = next((x for x in scenarios if x.get("kind") == "baseline"), scenarios[0] if scenarios else {})
    baseline_matrix = _scenario_matrix(matrix, baseline, app_version) if baseline else deepcopy(matrix)
    baseline_order = _order(baseline_matrix)
    baseline_scores = {str(x.get("alternative_id")): x.get("weighted_score") for x in baseline_matrix.get("alternative_summaries", []) if isinstance(x, dict)}
    results: List[Dict[str, Any]] = []
    score_history: Dict[str, List[float]] = {}
    ordering_changes: List[str] = []
    threshold_breaches: List[str] = []
    incomplete: List[str] = []
    max_swing = 0.0
    for scenario in scenarios:
        scenario_matrix = _scenario_matrix(matrix, scenario, app_version)
        sid = str(scenario.get("scenario_id") or "")
        order = _order(scenario_matrix)
        summaries = deepcopy(scenario_matrix.get("alternative_summaries", []))
        threshold_count = len(scenario_matrix.get("diagnostics", {}).get("threshold_violations", []))
        complete = bool(scenario_matrix.get("diagnostics", {}).get("complete"))
        ordering_changed = bool(baseline_order and order and order != baseline_order)
        if ordering_changed:
            ordering_changes.append(sid)
        if threshold_count:
            threshold_breaches.append(sid)
        if not complete:
            incomplete.append(sid)
        deltas = []
        for summary in summaries:
            aid = str(summary.get("alternative_id") or "")
            score = summary.get("weighted_score")
            if score is not None:
                score = float(score)
                score_history.setdefault(aid, []).append(score)
                baseline_score = baseline_scores.get(aid)
                delta = round(score - float(baseline_score), 4) if baseline_score is not None else None
                if delta is not None:
                    max_swing = max(max_swing, abs(delta))
                deltas.append({"alternative_id": aid, "score": round(score, 4), "delta_vs_baseline": delta})
        results.append({
            "scenario_id": sid,
            "name": scenario.get("name", sid),
            "kind": scenario.get("kind", "custom"),
            "matrix_id": scenario_matrix.get("matrix_id", ""),
            "complete": complete,
            "matrix_coverage_percent": scenario_matrix.get("diagnostics", {}).get("matrix_coverage_percent", 0.0),
            "threshold_violation_count": threshold_count,
            "ordering_changed_vs_baseline": ordering_changed,
            "alternative_scores": deltas,
            "boundary": "This scenario result is conditional on the scenario inputs and does not indicate scenario likelihood.",
        })
    ranges = []
    name_map = {str(x.get("alternative_id")): str(x.get("name") or x.get("alternative_id")) for x in matrix.get("alternatives_set", {}).get("alternatives", []) if isinstance(x, dict)}
    for aid, values in score_history.items():
        if not values:
            continue
        ranges.append({
            "alternative_id": aid,
            "name": name_map.get(aid, aid),
            "min_score": round(min(values), 4),
            "max_score": round(max(values), 4),
            "span": round(max(values) - min(values), 4),
        })
    fp = _fingerprint([scenario_set.get("scenario_set_id"), matrix.get("matrix_id"), results])
    return {
        "schema": SCENARIO_COMPARISON_SCHEMA,
        "version": app_version,
        "scenario_comparison_id": f"scenario-comparison-{fp[:16]}",
        "decision_id": decision_id or str(matrix.get("decision_id") or ""),
        "matrix_id": matrix.get("matrix_id", ""),
        "created_at": _utc_now(),
        "baseline_scenario_id": baseline.get("scenario_id", "") if baseline else "",
        "scenario_results": results,
        "alternative_score_ranges": ranges,
        "diagnostics": {
            "scenario_count": len(results),
            "complete_scenario_count": sum(1 for x in results if x.get("complete")),
            "ordering_change_scenario_ids": ordering_changes,
            "threshold_breach_scenario_ids": threshold_breaches,
            "incomplete_scenario_ids": incomplete,
            "max_score_swing": round(max_swing, 4),
        },
        "boundary": "Scenario comparison exposes conditional performance and instability. It does not predict which scenario will occur, choose a winner, or create a recommendation.",
    }


def run_stress_tests(
    comparison: Dict[str, Any],
    scenario_set: Dict[str, Any],
    confidence: Dict[str, Any],
    app_version: str,
    decision_id: str = "",
    config: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    config = deepcopy(config or {})
    max_drop = float(config.get("max_allowed_score_drop", 15.0))
    max_thresholds = int(config.get("max_allowed_threshold_violations", 0))
    require_complete = bool(config.get("require_complete_matrix", True))
    min_confidence = float(config.get("minimum_process_confidence", 0.0))
    scenario_map = {str(x.get("scenario_id")): x for x in scenario_set.get("scenarios", []) if isinstance(x, dict)}
    tests: List[Dict[str, Any]] = []
    failure_modes: List[Dict[str, Any]] = []
    ordering_changes = 0
    threshold_breaches = 0
    for result in comparison.get("scenario_results", []):
        if not isinstance(result, dict):
            continue
        sid = str(result.get("scenario_id") or "")
        scenario = scenario_map.get(sid, {})
        if scenario.get("kind") != "stress":
            continue
        deltas = [float(x.get("delta_vs_baseline")) for x in result.get("alternative_scores", []) if isinstance(x, dict) and x.get("delta_vs_baseline") is not None]
        worst_drop = min(deltas) if deltas else 0.0
        threshold_count = int(result.get("threshold_violation_count") or 0)
        complete = bool(result.get("complete"))
        ordering_changed = bool(result.get("ordering_changed_vs_baseline"))
        if ordering_changed:
            ordering_changes += 1
        if threshold_count:
            threshold_breaches += 1
        failures = []
        if worst_drop < -abs(max_drop):
            failures.append("score_drop_limit_exceeded")
        if threshold_count > max_thresholds:
            failures.append("threshold_violation_limit_exceeded")
        if require_complete and not complete:
            failures.append("matrix_incomplete")
        process_conf = float(confidence.get("process_confidence_index") or 0.0) if confidence.get("schema") == CONFIDENCE_ASSESSMENT_SCHEMA else 0.0
        if process_conf < min_confidence:
            failures.append("process_confidence_below_floor")
        passed = not failures
        tests.append({
            "scenario_id": sid,
            "name": result.get("name", sid),
            "passed": passed,
            "worst_score_delta": round(worst_drop, 4),
            "threshold_violation_count": threshold_count,
            "matrix_complete": complete,
            "ordering_changed_vs_baseline": ordering_changed,
            "process_confidence_index": process_conf,
            "failure_codes": failures,
        })
        for code in failures:
            failure_modes.append({"scenario_id": sid, "failure_code": code})
    fp = _fingerprint([comparison.get("scenario_comparison_id"), tests, config])
    return {
        "schema": STRESS_TEST_SUITE_SCHEMA,
        "version": app_version,
        "stress_test_suite_id": f"stress-test-suite-{fp[:16]}",
        "decision_id": decision_id or str(comparison.get("decision_id") or ""),
        "created_at": _utc_now(),
        "tests": tests,
        "failure_modes": failure_modes,
        "diagnostics": {
            "test_count": len(tests),
            "passed_count": sum(1 for x in tests if x.get("passed")),
            "failed_count": sum(1 for x in tests if not x.get("passed")),
            "stress_scenario_count": len(tests),
            "ordering_change_count": ordering_changes,
            "threshold_breach_count": threshold_breaches,
        },
        "configuration": {
            "max_allowed_score_drop": max_drop,
            "max_allowed_threshold_violations": max_thresholds,
            "require_complete_matrix": require_complete,
            "minimum_process_confidence": min_confidence,
        },
        "boundary": "Stress tests identify conditions under which the comparison becomes fragile, incomplete, or constraint-violating. Passing a stress test is not approval, certification, or a recommendation.",
    }


def attach_scenario_stress(
    decision_object: Dict[str, Any],
    scenario_set: Dict[str, Any],
    comparison: Dict[str, Any],
    stress_suite: Dict[str, Any],
    app_version: str,
) -> Dict[str, Any]:
    out = deepcopy(decision_object or {})
    out.setdefault("scenario_sets", [])
    out.setdefault("scenario_comparisons", [])
    out.setdefault("stress_test_suites", [])
    out["scenario_sets"] = [x for x in out["scenario_sets"] if isinstance(x, dict) and x.get("scenario_set_id") != scenario_set.get("scenario_set_id")] + [deepcopy(scenario_set)]
    out["scenario_comparisons"] = [x for x in out["scenario_comparisons"] if isinstance(x, dict) and x.get("scenario_comparison_id") != comparison.get("scenario_comparison_id")] + [deepcopy(comparison)]
    out["stress_test_suites"] = [x for x in out["stress_test_suites"] if isinstance(x, dict) and x.get("stress_test_suite_id") != stress_suite.get("stress_test_suite_id")] + [deepcopy(stress_suite)]
    out["scenarios"] = deepcopy(scenario_set.get("scenarios", []))
    out.setdefault("provenance", {}).setdefault("records", []).append({
        "at": _utc_now(),
        "action": "scenario_comparison_stress_tests_attached",
        "scenario_set_id": scenario_set.get("scenario_set_id", ""),
        "scenario_comparison_id": comparison.get("scenario_comparison_id", ""),
        "stress_test_suite_id": stress_suite.get("stress_test_suite_id", ""),
    })
    out["updated_at"] = _utc_now()
    out["version"] = app_version
    return out
