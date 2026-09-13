from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

CONNECTED_DECISION_INTELLIGENCE_SCHEMA = "scds-connected-decision-intelligence/3.0"
DECISION_LIFECYCLE_STATE_SCHEMA = "scds-decision-lifecycle-state/1.0"
DECISION_READINESS_MATRIX_SCHEMA = "scds-decision-readiness-matrix/1.0"
CROSS_PRODUCT_ROUTE_PLAN_SCHEMA = "scds-cross-product-route-plan/1.0"

BOUNDARY = (
    "Connected Decision Intelligence summarizes recorded decision work and proposes bounded next-action routes. "
    "Readiness is not approval, lifecycle position is not an automatic transition, route plans do not execute external work, "
    "and Decision Studio does not select a winner or authorize consequential action."
)

STAGES = [
    ("frame", "Frame"),
    ("evidence", "Evidence"),
    ("analyze", "Analyze"),
    ("compare", "Compare"),
    ("stress", "Stress"),
    ("review", "Review"),
    ("decide", "Decide"),
    ("monitor", "Monitor"),
]

ROUTES = {
    "frame": ["decision-studio"],
    "evidence": ["knowledge-library", "research-librarian", "site-intelligence"],
    "analyze": ["research-lab", "workbench"],
    "compare": ["decision-studio", "workbench"],
    "stress": ["decision-studio", "research-lab", "workbench", "site-intelligence"],
    "review": ["decision-studio", "research-librarian"],
    "decide": ["decision-studio"],
    "monitor": ["site-intelligence", "decision-studio"],
}

class ConnectedDecisionIntelligenceRequest(BaseModel):
    packet: Dict[str, Any] = Field(default_factory=dict)
    decisionObject: Dict[str, Any] = Field(default_factory=dict)
    connectedIntelligence: Dict[str, Any] = Field(default_factory=dict)
    requestedStage: str = ""
    actor: str = ""
    notes: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _nonempty(value: Any) -> bool:
    return value not in (None, "", [], {})


def _packet_to_minimal_object(packet: Dict[str, Any], app_version: str) -> Dict[str, Any]:
    p = _dict(packet)
    return {
        "schema": "scds-decision-object/1.0",
        "version": app_version,
        "decision_id": str(p.get("decision_packet_id") or ""),
        "question": str(p.get("decision_question") or _dict(p.get("decision_framing")).get("decision_question") or ""),
        "objective": str(_dict(p.get("decision_framing")).get("objective") or ""),
        "evidence": deepcopy(_list(p.get("evidence_registry"))),
        "evidence_bundles": deepcopy(_list(p.get("evidence_bundles"))),
        "models": deepcopy(_list(p.get("models")) or _list(p.get("technical_artifacts"))),
        "analysis_handoffs": deepcopy(_list(p.get("analysis_handoffs"))),
        "computation_handoffs": deepcopy(_list(p.get("computation_handoffs"))),
        "criteria": deepcopy(_list(p.get("criteria_registry")) or _list(p.get("criteria"))),
        "alternatives": deepcopy(_list(p.get("alternatives"))),
        "tradeoff_matrices": deepcopy(_list(p.get("tradeoff_matrices")) or ([p.get("tradeoff_matrix")] if isinstance(p.get("tradeoff_matrix"), dict) else [])),
        "uncertainties": deepcopy(_list(p.get("uncertainties"))),
        "uncertainty_registers": deepcopy(_list(p.get("uncertainty_registers")) or ([p.get("uncertainty_register")] if isinstance(p.get("uncertainty_register"), dict) else [])),
        "sensitivity_analyses": deepcopy(_list(p.get("sensitivity_analyses")) or ([p.get("sensitivity_analysis")] if isinstance(p.get("sensitivity_analysis"), dict) else [])),
        "scenario_sets": deepcopy(_list(p.get("scenario_sets")) or ([p.get("scenario_set")] if isinstance(p.get("scenario_set"), dict) else [])),
        "scenario_comparisons": deepcopy(_list(p.get("scenario_comparisons")) or ([p.get("scenario_comparison")] if isinstance(p.get("scenario_comparison"), dict) else [])),
        "stress_test_suites": deepcopy(_list(p.get("stress_test_suites")) or ([p.get("stress_test_suite")] if isinstance(p.get("stress_test_suite"), dict) else [])),
        "site_intelligence_contexts": deepcopy(_list(p.get("site_intelligence_contexts"))),
        "dependency_graphs": deepcopy(_list(p.get("dependency_graphs")) or ([p.get("decision_dependency_graph")] if isinstance(p.get("decision_dependency_graph"), dict) else [])),
        "recommendation_candidates": deepcopy(_list(p.get("recommendation_candidates"))),
        "recommendation_reviews": deepcopy(_list(p.get("recommendation_reviews"))),
        "decision": deepcopy(_dict(p.get("decision")) or _dict(p.get("decision_record"))),
        "outcome_review": deepcopy(_dict(p.get("outcome_review")) or _dict(p.get("outcome_monitoring"))),
        "platform_context": deepcopy(_dict(p.get("platform_context"))),
        "provenance": {"records": []},
    }


def _stage_rows(obj: Dict[str, Any]) -> List[Dict[str, Any]]:
    evidence_count = len(_list(obj.get("evidence"))) + len(_list(obj.get("evidence_bundles"))) + len(_list(obj.get("site_intelligence_contexts")))
    analysis_count = len(_list(obj.get("models"))) + len(_list(obj.get("analysis_handoffs"))) + len(_list(obj.get("computation_handoffs")))
    compare_count = len(_list(obj.get("tradeoff_matrices")))
    alternatives_count = len(_list(obj.get("alternatives")))
    criteria_count = len(_list(obj.get("criteria")))
    stress_count = len(_list(obj.get("stress_test_suites"))) + len(_list(obj.get("scenario_comparisons"))) + len(_list(obj.get("sensitivity_analyses"))) + len(_list(obj.get("uncertainty_registers")))
    graph_count = len(_list(obj.get("dependency_graphs")))
    candidates = _list(obj.get("recommendation_candidates"))
    reviews = _list(obj.get("recommendation_reviews"))
    latest_review = _dict(reviews[-1]) if reviews else {}
    human_disposition = _dict(latest_review.get("human_disposition"))
    decision = _dict(obj.get("decision"))
    outcome = _dict(obj.get("outcome_review"))

    facts = {
        "frame": {
            "requirements": ["decision question"],
            "met": ["decision question"] if str(obj.get("question") or "").strip() else [],
            "signals": {"question": bool(str(obj.get("question") or "").strip()), "objective": bool(str(obj.get("objective") or "").strip())},
        },
        "evidence": {
            "requirements": ["reviewable evidence or contextual source"],
            "met": ["reviewable evidence or contextual source"] if evidence_count else [],
            "signals": {"evidence_records": evidence_count, "site_context_bundles": len(_list(obj.get("site_intelligence_contexts")))},
        },
        "analyze": {
            "requirements": ["analysis, model, or computation artifact"],
            "met": ["analysis, model, or computation artifact"] if analysis_count else [],
            "signals": {"analysis_artifacts": analysis_count},
        },
        "compare": {
            "requirements": ["two or more alternatives", "criteria", "tradeoff matrix"],
            "met": (["two or more alternatives"] if alternatives_count >= 2 else []) + (["criteria"] if criteria_count else []) + (["tradeoff matrix"] if compare_count else []),
            "signals": {"alternatives": alternatives_count, "criteria": criteria_count, "tradeoff_matrices": compare_count},
        },
        "stress": {
            "requirements": ["uncertainty, sensitivity, scenario, or stress analysis"],
            "met": ["uncertainty, sensitivity, scenario, or stress analysis"] if stress_count else [],
            "signals": {"stress_analysis_artifacts": stress_count},
        },
        "review": {
            "requirements": ["dependency graph", "recommendation candidate", "human review disposition"],
            "met": (["dependency graph"] if graph_count else []) + (["recommendation candidate"] if candidates else []) + (["human review disposition"] if human_disposition else []),
            "signals": {"dependency_graphs": graph_count, "recommendation_candidates": len(candidates), "recommendation_reviews": len(reviews), "human_disposition_recorded": bool(human_disposition), "decision_ready": bool(latest_review.get("decision_ready", False))},
        },
        "decide": {
            "requirements": ["explicit human decision record"],
            "met": ["explicit human decision record"] if decision else [],
            "signals": {"decision_recorded": bool(decision)},
        },
        "monitor": {
            "requirements": ["outcome or monitoring record"],
            "met": ["outcome or monitoring record"] if outcome else [],
            "signals": {"outcome_monitoring_recorded": bool(outcome)},
        },
    }

    rows: List[Dict[str, Any]] = []
    for stage_id, label in STAGES:
        row = facts[stage_id]
        requirements = row["requirements"]
        met = row["met"]
        missing = [x for x in requirements if x not in met]
        if not requirements:
            status = "ready"
        elif len(met) == len(requirements):
            status = "ready"
        elif met:
            status = "in_progress"
        else:
            status = "not_started"
        rows.append({
            "stage_id": stage_id,
            "label": label,
            "status": status,
            "requirements": requirements,
            "met_requirements": met,
            "missing_requirements": missing,
            "signals": row["signals"],
            "product_routes": deepcopy(ROUTES[stage_id]),
        })
    return rows


def readiness_matrix_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": DECISION_READINESS_MATRIX_SCHEMA,
        "version": app_version,
        "stages": [{"stage_id": sid, "label": label, "status": "not_started", "requirements": [], "met_requirements": [], "missing_requirements": [], "signals": {}, "product_routes": deepcopy(ROUTES[sid])} for sid, label in STAGES],
        "summary": {"ready_stage_count": 0, "total_stage_count": len(STAGES), "completion_percent": 0.0},
        "boundary": BOUNDARY,
    }


def lifecycle_state_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": DECISION_LIFECYCLE_STATE_SCHEMA,
        "version": app_version,
        "current_stage": "frame",
        "next_stage": "evidence",
        "completed_stages": [],
        "blocked_stages": [],
        "automatic_transition": False,
        "human_transition_required": True,
        "boundary": BOUNDARY,
    }


def route_plan_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": CROSS_PRODUCT_ROUTE_PLAN_SCHEMA,
        "version": app_version,
        "routes": [],
        "external_execution_performed": False,
        "automatic_delivery": False,
        "boundary": BOUNDARY,
    }


def connected_intelligence_template(app_version: str) -> Dict[str, Any]:
    return {
        "schema": CONNECTED_DECISION_INTELLIGENCE_SCHEMA,
        "version": app_version,
        "decision_id": "",
        "generated_at": "",
        "readiness_matrix": readiness_matrix_template(app_version),
        "lifecycle_state": lifecycle_state_template(app_version),
        "route_plan": route_plan_template(app_version),
        "cross_product_lineage": [],
        "human_control": {
            "winner_selection_automatic": False,
            "recommendation_automatic": False,
            "stage_transition_automatic": False,
            "approval_automatic": False,
            "external_execution_automatic": False,
        },
        "boundary": BOUNDARY,
    }


def _lineage(obj: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    mapping = [
        ("knowledge-library", "evidence", "evidence_bundles"),
        ("site-intelligence", "real_world_context", "site_intelligence_contexts"),
        ("research-lab", "analysis", "analysis_handoffs"),
        ("workbench", "computation", "computation_handoffs"),
        ("decision-studio", "dependency_mapping", "dependency_graphs"),
        ("decision-studio", "recommendation_review", "recommendation_reviews"),
    ]
    for product, role, key in mapping:
        values = _list(obj.get(key))
        if values:
            rows.append({"product": product, "role": role, "artifact_collection": key, "artifact_count": len(values)})
    platform = _dict(obj.get("platform_context"))
    for link in _list(platform.get("artifact_links")):
        if isinstance(link, dict):
            row = deepcopy(link)
            row.setdefault("product", str(link.get("product_id") or link.get("product") or "unknown"))
            row.setdefault("role", "platform_context")
            rows.append(row)
    return rows


def _route_plan(rows: List[Dict[str, Any]], app_version: str) -> Dict[str, Any]:
    routes: List[Dict[str, Any]] = []
    for row in rows:
        if row["status"] == "ready":
            continue
        for product in row["product_routes"]:
            routes.append({
                "stage_id": row["stage_id"],
                "product": product,
                "reason": "; ".join(row["missing_requirements"]) or "stage review",
                "status": "suggested",
                "execution_performed": False,
                "requires_explicit_handoff": product != "decision-studio",
            })
        if routes:
            break
    plan = route_plan_template(app_version)
    plan["routes"] = routes
    plan["route_count"] = len(routes)
    plan["plan_fingerprint"] = _hash({k: v for k, v in plan.items() if k != "plan_fingerprint"})
    return plan


def build_connected_intelligence(decision_object: Dict[str, Any], *, app_version: str, packet: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    obj = deepcopy(decision_object) if isinstance(decision_object, dict) and decision_object else _packet_to_minimal_object(packet or {}, app_version)
    rows = _stage_rows(obj)
    ready = [r["stage_id"] for r in rows if r["status"] == "ready"]
    blocked = [r["stage_id"] for r in rows if r["status"] != "ready"]
    current = blocked[0] if blocked else "monitor"
    idx = [s[0] for s in STAGES].index(current)
    next_stage = STAGES[min(idx + 1, len(STAGES) - 1)][0] if current else "monitor"
    matrix = {
        "schema": DECISION_READINESS_MATRIX_SCHEMA,
        "version": app_version,
        "generated_at": _now(),
        "stages": rows,
        "summary": {
            "ready_stage_count": len(ready),
            "total_stage_count": len(STAGES),
            "completion_percent": round((len(ready) / len(STAGES)) * 100.0, 1),
            "first_incomplete_stage": current if blocked else "",
        },
        "boundary": BOUNDARY,
    }
    matrix["readiness_fingerprint"] = _hash({k: v for k, v in matrix.items() if k not in {"generated_at", "readiness_fingerprint"}})
    lifecycle = {
        "schema": DECISION_LIFECYCLE_STATE_SCHEMA,
        "version": app_version,
        "decision_id": str(obj.get("decision_id") or ""),
        "current_stage": current,
        "next_stage": next_stage,
        "completed_stages": ready,
        "blocked_stages": blocked,
        "automatic_transition": False,
        "human_transition_required": True,
        "generated_at": _now(),
        "boundary": BOUNDARY,
    }
    lifecycle["state_fingerprint"] = _hash({k: v for k, v in lifecycle.items() if k not in {"generated_at", "state_fingerprint"}})
    route_plan = _route_plan(rows, app_version)
    out = {
        "schema": CONNECTED_DECISION_INTELLIGENCE_SCHEMA,
        "version": app_version,
        "decision_id": str(obj.get("decision_id") or ""),
        "generated_at": _now(),
        "readiness_matrix": matrix,
        "lifecycle_state": lifecycle,
        "route_plan": route_plan,
        "cross_product_lineage": _lineage(obj),
        "human_control": {
            "winner_selection_automatic": False,
            "recommendation_automatic": False,
            "stage_transition_automatic": False,
            "approval_automatic": False,
            "external_execution_automatic": False,
        },
        "boundary": BOUNDARY,
    }
    out["connected_intelligence_id"] = "connected-intelligence:" + _hash({"decision_id": out["decision_id"], "matrix": matrix["readiness_fingerprint"], "routes": route_plan.get("plan_fingerprint", "")})[:20]
    out["connected_intelligence_fingerprint"] = _hash({k: v for k, v in out.items() if k not in {"generated_at", "connected_intelligence_fingerprint"}})
    return out


def validate_connected_intelligence(value: Dict[str, Any], *, app_version: str) -> Dict[str, Any]:
    x = value if isinstance(value, dict) else {}
    errors: List[str] = []
    if x.get("schema") != CONNECTED_DECISION_INTELLIGENCE_SCHEMA:
        errors.append("connected intelligence schema is invalid")
    for key, schema in [
        ("readiness_matrix", DECISION_READINESS_MATRIX_SCHEMA),
        ("lifecycle_state", DECISION_LIFECYCLE_STATE_SCHEMA),
        ("route_plan", CROSS_PRODUCT_ROUTE_PLAN_SCHEMA),
    ]:
        if _dict(x.get(key)).get("schema") != schema:
            errors.append(f"{key} schema is invalid")
    control = _dict(x.get("human_control"))
    for key in ["winner_selection_automatic", "recommendation_automatic", "stage_transition_automatic", "approval_automatic", "external_execution_automatic"]:
        if control.get(key) is True:
            errors.append(f"{key} must remain false")
    supplied = str(x.get("connected_intelligence_fingerprint") or "")
    if supplied:
        expected = _hash({k: v for k, v in x.items() if k not in {"generated_at", "connected_intelligence_fingerprint"}})
        if supplied != expected:
            errors.append("connected intelligence fingerprint does not match payload")
    return {"valid": not errors, "version": app_version, "errors": errors, "boundary": BOUNDARY}


def attach_connected_intelligence(decision_object: Dict[str, Any], intelligence: Dict[str, Any], *, app_version: str) -> Dict[str, Any]:
    obj = deepcopy(decision_object or {})
    obj.setdefault("schema", "scds-decision-object/1.0")
    obj["version"] = app_version
    obj.setdefault("connected_decision_intelligence", [])
    obj["connected_decision_intelligence"].append(deepcopy(intelligence))
    obj["connected_intelligence"] = deepcopy(intelligence)
    provenance = obj.setdefault("provenance", {})
    records = provenance.setdefault("records", [])
    records.append({
        "action": "connected_decision_intelligence_attached",
        "at": _now(),
        "version": app_version,
        "connected_intelligence_id": intelligence.get("connected_intelligence_id", ""),
        "fingerprint": intelligence.get("connected_intelligence_fingerprint", ""),
    })
    return obj
