"""Governed Workspace execution adapter (SC-SIM-01 G8).

Workspace owns orchestration, permissions, ExecutionRuns and receipts; Decision Studio keeps its decision
logic and decision objects. This adapter lets the Workspace job fabric call two existing Decision Studio
analyses through one authenticated endpoint, so their results carry a Workspace runtime receipt:

- ``workspace.decision-studio.scenario-comparison`` -> build_tradeoff_matrix, build_scenario_set,
  compare_scenarios
- ``workspace.decision-studio.sensitivity-analysis`` -> build_tradeoff_matrix, build_uncertainty_register,
  run_sensitivity_analysis

Nothing is reimplemented, no decision object is created or changed, and no recommendation or approval is
produced. Analyses run any other way remain exploratory: they have no Workspace receipt.
"""
from __future__ import annotations

import hmac
import os
import platform
from typing import Any, Callable, Dict, List

from fastapi import Header, HTTPException

from app.scenario_stress import build_scenario_set, compare_scenarios
from app.tradeoff_matrix import build_tradeoff_matrix
from app.uncertainty_confidence import build_uncertainty_register, run_sensitivity_analysis

ENVELOPE_SCHEMA = "sc-workspace-polyglot-execution-envelope/1.0"
RESULT_SCHEMA = "scds-workspace-adapter-result/1.0"
RUNTIME = "decision-studio-analysis"
TOKEN_ENV = "SCDS_WORKSPACE_ADAPTER_TOKEN"
MAX_ITEMS = 200


def _app_version() -> str:
    from app.services.decision_service import APP_VERSION  # late: the service module is large
    return APP_VERSION


def _records(payload: Dict[str, Any], key: str, required: bool = True) -> List[Dict[str, Any]]:
    value = payload.get(key, [] if not required else None)
    if not isinstance(value, list) or (required and not value) or len(value) > MAX_ITEMS \
            or not all(isinstance(x, dict) for x in value):
        raise HTTPException(status_code=422, detail=f"{key} must be a list of 1-{MAX_ITEMS} objects")
    return value


def _matrix(payload: Dict[str, Any]) -> Dict[str, Any]:
    return build_tradeoff_matrix(_records(payload, "criteria"), _records(payload, "alternatives"),
                                 _records(payload, "evaluations"), _app_version(),
                                 decision_id=str(payload.get("decisionId") or "")[:160])


def _scenario_comparison(payload: Dict[str, Any]) -> Dict[str, Any]:
    matrix = _matrix(payload)
    scenario_set = build_scenario_set(_records(payload, "scenarios"), matrix, _app_version(), decision_id=matrix.get("decision_id", ""))
    return {"tradeoffMatrix": matrix, "scenarioSet": scenario_set,
            "scenarioComparison": compare_scenarios(matrix, scenario_set, _app_version(), decision_id=matrix.get("decision_id", ""))}


def _sensitivity(payload: Dict[str, Any]) -> Dict[str, Any]:
    matrix = _matrix(payload)
    config = payload.get("sensitivityConfig") or {}
    if not isinstance(config, dict):
        raise HTTPException(status_code=422, detail="sensitivityConfig must be an object")
    register = build_uncertainty_register(_records(payload, "uncertainties", required=False), matrix, _app_version(),
                                          decision_id=matrix.get("decision_id", ""))
    return {"tradeoffMatrix": matrix, "uncertaintyRegister": register,
            "sensitivityAnalysis": run_sensitivity_analysis(matrix, register, _app_version(),
                                                            decision_id=matrix.get("decision_id", ""), config=config)}


OPERATIONS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "workspace.decision-studio.scenario-comparison": _scenario_comparison,
    "workspace.decision-studio.sensitivity-analysis": _sensitivity,
}


def _authorize(authorization: str | None) -> None:
    token = os.getenv(TOKEN_ENV, "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Workspace execution adapter is not configured")
    if not authorization or not hmac.compare_digest(authorization.strip().encode(), f"Bearer {token}".encode()):
        raise HTTPException(status_code=401, detail="Workspace execution adapter authentication failed")


def adapter_status() -> Dict[str, Any]:
    return {"schema": "scds-workspace-adapter-status/1.0", "runtime": RUNTIME, "version": _app_version(),
            "operations": sorted(OPERATIONS), "configured": bool(os.getenv(TOKEN_ENV, "").strip()),
            "receiptAuthority": "workspace", "decisionObjectsChanged": False}


def execute(envelope: Dict[str, Any], authorization: str | None = Header(default=None)) -> Dict[str, Any]:
    _authorize(authorization)
    if envelope.get("schema") != ENVELOPE_SCHEMA or envelope.get("language") != "decision-studio":
        raise HTTPException(status_code=400, detail="Unsupported Workspace execution envelope")
    if envelope.get("arbitraryCodeExecution") is not False:
        raise HTTPException(status_code=400, detail="Arbitrary-code execution must remain disabled")
    operation = str(envelope.get("operation") or "")
    handler = OPERATIONS.get(operation)
    if handler is None:
        raise HTTPException(status_code=400, detail="Decision Studio operation is not a governed adapter operation")
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload must be an object")
    result = handler(payload)
    return {"ok": True, "schema": RESULT_SCHEMA, "runtime": RUNTIME, "operation": operation,
            "requestFingerprint": envelope.get("requestFingerprint"),
            "numericalLibraries": {"source": "runtime", "runtime": f"decision-studio {_app_version()}",
                                   "python": platform.python_version(), "arithmetic": "python-float",
                                   "precision": "ieee754-binary64"},
            "decisionObjectsChanged": False, "recommendationProduced": False, "result": result}
