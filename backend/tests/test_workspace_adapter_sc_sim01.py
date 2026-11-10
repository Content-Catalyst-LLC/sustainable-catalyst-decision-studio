"""SC-SIM-01 G8: the governed Workspace execution adapter calls existing Decision Studio analyses only."""
import pytest
from fastapi.testclient import TestClient

from app import workspace_adapter as wa
from app.main import app
from app.scenario_stress import build_scenario_set, compare_scenarios
from app.services.decision_service import APP_VERSION
from app.tradeoff_matrix import build_tradeoff_matrix
from tests.test_backend import _v240_matrix_payload, _v240_uncertainties, _v250_scenarios

client = TestClient(app)
TOKEN = "adapter-test-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def envelope(operation, payload, **over):
    return {"schema": wa.ENVELOPE_SCHEMA, "language": "decision-studio", "operation": operation, "payload": payload,
            "requestFingerprint": "f" * 64, "arbitraryCodeExecution": False, **over}


@pytest.fixture(autouse=True)
def token(monkeypatch):
    monkeypatch.setenv(wa.TOKEN_ENV, TOKEN)


def comparison_payload():
    return {**_v240_matrix_payload(), "scenarios": _v250_scenarios()}


def without_times(value):
    if isinstance(value, dict):
        return {k: without_times(v) for k, v in value.items() if k not in {"created_at", "updated_at", "at"}}
    if isinstance(value, list):
        return [without_times(v) for v in value]
    return value


def test_scenario_comparison_is_the_existing_decision_studio_analysis():
    r = client.post("/v1/workspace/execute", headers=AUTH, json=envelope("workspace.decision-studio.scenario-comparison", comparison_payload()))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["schema"] == wa.RESULT_SCHEMA and body["decisionObjectsChanged"] is False and body["recommendationProduced"] is False
    p = comparison_payload()
    matrix = build_tradeoff_matrix(p["criteria"], p["alternatives"], p["evaluations"], APP_VERSION)
    direct = compare_scenarios(matrix, build_scenario_set(p["scenarios"], matrix, APP_VERSION), APP_VERSION)
    got = body["result"]["scenarioComparison"]
    assert without_times(got) == without_times(direct)
    assert got["diagnostics"]["scenario_count"] == 3 and "winner" not in got


def test_sensitivity_analysis_runs():
    payload = {**_v240_matrix_payload(), "uncertainties": _v240_uncertainties()}
    r = client.post("/v1/workspace/execute", headers=AUTH, json=envelope("workspace.decision-studio.sensitivity-analysis", payload))
    assert r.status_code == 200, r.text
    assert r.json()["result"]["sensitivityAnalysis"]["schema"] == "scds-sensitivity-analysis/1.0"


@pytest.mark.parametrize("headers,status", [({}, 401), ({"Authorization": "Bearer wrong"}, 401)])
def test_authentication_is_required(headers, status):
    r = client.post("/v1/workspace/execute", headers=headers, json=envelope("workspace.decision-studio.scenario-comparison", comparison_payload()))
    assert r.status_code == status


def test_unconfigured_adapter_refuses(monkeypatch):
    monkeypatch.delenv(wa.TOKEN_ENV)
    r = client.post("/v1/workspace/execute", headers=AUTH, json=envelope("workspace.decision-studio.scenario-comparison", comparison_payload()))
    assert r.status_code == 503 and client.get("/v1/workspace/adapter").json()["configured"] is False


@pytest.mark.parametrize("env,status", [
    ({"language": "decision"}, 400), ({"schema": "x"}, 400), ({"arbitraryCodeExecution": True}, 400),
    ({"operation": "workspace.decision-studio.approve"}, 400), ({"payload": []}, 400),
    ({"payload": {"criteria": [], "alternatives": [], "evaluations": [], "scenarios": []}}, 422),
])
def test_envelope_refusals(env, status):
    r = client.post("/v1/workspace/execute", headers=AUTH,
                    json={**envelope("workspace.decision-studio.scenario-comparison", comparison_payload()), **env})
    assert r.status_code == status
