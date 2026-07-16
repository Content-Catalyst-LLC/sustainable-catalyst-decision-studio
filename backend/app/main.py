from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import json
import math
import os
import threading
import time
import urllib.request
import urllib.error

APP_VERSION = "1.7.1"
BUILD_FINGERPRINT = os.getenv("SCDS_BUILD_FINGERPRINT", "scds-v1.7.1-53b729b")
SOURCE_COMMIT = os.getenv("SCDS_SOURCE_COMMIT", "53b729b6940bc6455cf7815c58951bce4a36fff7")
RELEASE_DATE = "2026-07-16"
DECISION_PACKET_SCHEMA = "scds-decision-packet/1.0"
MAX_REQUEST_BYTES = max(65536, int(os.getenv("SCDS_MAX_REQUEST_BYTES", "1048576")))
PUBLIC_RATE_LIMIT = max(10, int(os.getenv("SCDS_PUBLIC_RATE_LIMIT", "60")))
RATE_WINDOW_SECONDS = max(10, int(os.getenv("SCDS_RATE_WINDOW_SECONDS", "60")))
STARTED_AT_MONOTONIC = time.monotonic()
_RATE_BUCKETS: Dict[str, List[float]] = {}
_RATE_LOCK = threading.Lock()
EXPENSIVE_PUBLIC_PATHS = {
    "/analyze", "/brief", "/report", "/integrated-brief",
    "/decision-packet/brief", "/decision-packet/analyze",
    "/brief-readiness", "/decision-packet/readiness", "/review/status",
    "/scenario-comparison", "/decision-packet/scenario-comparison",
    "/workbench/handoff", "/decision-packet/workbench-handoff",
    "/integrations/import", "/decision-packet/import",
    "/decision-packet/save-template", "/export-center/bundle",
    "/decision-packet/export-bundle", "/audit/generate",
}

app = FastAPI(title="Sustainable Catalyst Decision Studio Backend", version=APP_VERSION)


def release_manifest() -> Dict[str, Any]:
    return {
        "release": APP_VERSION,
        "release_name": "Production Reliability and Roadmap Repair",
        "release_date": RELEASE_DATE,
        "build_fingerprint": BUILD_FINGERPRINT,
        "source_commit": SOURCE_COMMIT,
        "decision_packet_schema": DECISION_PACKET_SCHEMA,
        "compatibility": {
            "wordpress_plugin": APP_VERSION,
            "backend": APP_VERSION,
            "api_namespace": "scds/v1",
            "shortcodes_preserved": True,
            "packet_schema_breaking_changes": False,
        },
    }


def _request_client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    host = forwarded or (request.client.host if request.client else "unknown")
    return f"{host}:{request.url.path}"


def _rate_limit_exceeded(key: str, now: Optional[float] = None) -> bool:
    current = time.monotonic() if now is None else now
    cutoff = current - RATE_WINDOW_SECONDS
    with _RATE_LOCK:
        bucket = [stamp for stamp in _RATE_BUCKETS.get(key, []) if stamp > cutoff]
        if len(bucket) >= PUBLIC_RATE_LIMIT:
            _RATE_BUCKETS[key] = bucket
            return True
        bucket.append(current)
        _RATE_BUCKETS[key] = bucket
        if len(_RATE_BUCKETS) > 2048:
            stale = [bucket_key for bucket_key, stamps in _RATE_BUCKETS.items() if not stamps or stamps[-1] <= cutoff]
            for bucket_key in stale[:1024]:
                _RATE_BUCKETS.pop(bucket_key, None)
    return False


@app.middleware("http")
async def production_request_guard(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH"}:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_REQUEST_BYTES:
                    return JSONResponse(status_code=413, content={"ok": False, "error": "request_too_large", "max_request_bytes": MAX_REQUEST_BYTES})
            except ValueError:
                return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_content_length"})
        body = await request.body()
        if len(body) > MAX_REQUEST_BYTES:
            return JSONResponse(status_code=413, content={"ok": False, "error": "request_too_large", "max_request_bytes": MAX_REQUEST_BYTES})

        if request.url.path in EXPENSIVE_PUBLIC_PATHS:
            expected_key = os.getenv("SCDS_API_KEY", "").strip()
            supplied_key = request.headers.get("x-scds-api-key", "").strip()
            trusted = bool(expected_key and supplied_key and supplied_key == expected_key)
            if not trusted and _rate_limit_exceeded(_request_client_key(request)):
                return JSONResponse(
                    status_code=429,
                    content={"ok": False, "error": "rate_limit_exceeded", "limit": PUBLIC_RATE_LIMIT, "window_seconds": RATE_WINDOW_SECONDS},
                    headers={"Retry-After": str(RATE_WINDOW_SECONDS)},
                )

    response = await call_next(request)
    response.headers["X-SCDS-Version"] = APP_VERSION
    response.headers["X-SCDS-Build"] = BUILD_FINGERPRINT
    return response

class DecisionInputs(BaseModel):
    projectName: str = "Fleet electrification decision"
    orgType: str = "Mid-sized logistics company"
    sector: str = "Transportation and logistics"
    location: str = "United States / Midwest"
    horizon: str = "5 years"
    decisionType: str = "Capital project"
    decisionQuestion: str = "Should the project move forward?"
    constraints: str = ""
    baselineEmissions: float = Field(1200, ge=0)
    reductionRate: float = Field(32, ge=0, le=100)
    adoptionRate: float = Field(65, ge=0, le=100)
    capex: float = Field(950000, ge=0)
    annualSavings: float = Field(185000, ge=0)
    discountRate: float = Field(7, ge=0, le=100)
    modelYears: int = Field(5, ge=1, le=50)
    complexity: str = "Medium"
    weightEnv: float = 30
    weightSocial: float = 20
    weightEconomic: float = 30
    weightGovernance: float = 20
    exposure: float = Field(55, ge=0, le=100)
    vulnerability: float = Field(48, ge=0, le=100)
    resilience: float = Field(62, ge=0, le=100)
    stakeholderSensitivity: float = Field(45, ge=0, le=100)
    governanceReadiness: float = Field(68, ge=0, le=100)
    dataConfidence: float = Field(70, ge=0, le=100)
    socialBenefit: float = Field(58, ge=0, le=100)
    savingsVolatility: float = Field(15, ge=0, le=100)
    capexVolatility: float = Field(18, ge=0, le=100)
    carbonPrice: float = Field(45, ge=0)

class BriefRequest(BaseModel):
    inputs: DecisionInputs = Field(default_factory=DecisionInputs)
    results: Optional[Dict[str, Any]] = None
    briefType: str = "decision_brief"
    audience: str = "public-interest decision reviewer"
    useAI: bool = True

class ReportRequest(BaseModel):
    inputs: DecisionInputs = Field(default_factory=DecisionInputs)
    includeAI: bool = True

class DecisionPacketRequest(BaseModel):
    inputs: Optional[DecisionInputs] = None
    packet: Dict[str, Any] = Field(default_factory=dict)
    moduleArtifacts: Dict[str, Any] = Field(default_factory=dict)
    notes: str = ""

class AuditProvenanceRequest(BaseModel):
    inputs: DecisionInputs = Field(default_factory=DecisionInputs)
    results: Optional[Dict[str, Any]] = None
    packet: Dict[str, Any] = Field(default_factory=dict)
    moduleArtifacts: Dict[str, Any] = Field(default_factory=dict)
    reviewStatus: str = "draft"
    preparedBy: str = ""
    reviewedBy: str = ""
    notes: str = ""


class ArtifactImportRequest(BaseModel):
    artifact: Dict[str, Any] = Field(default_factory=dict)
    moduleId: Optional[str] = None
    packet: Dict[str, Any] = Field(default_factory=dict)
    preserveRaw: bool = True
    notes: str = ""


class IntegratedBriefRequest(BaseModel):
    inputs: DecisionInputs = Field(default_factory=DecisionInputs)
    results: Optional[Dict[str, Any]] = None
    packet: Dict[str, Any] = Field(default_factory=dict)
    moduleArtifacts: Dict[str, Any] = Field(default_factory=dict)
    audit: Optional[Dict[str, Any]] = None
    audience: str = "Sustainable Catalyst decision reviewer"
    includeAI: bool = False
    exportFormat: str = "structured"
    notes: str = ""


class BriefReadinessRequest(BaseModel):
    inputs: DecisionInputs = Field(default_factory=DecisionInputs)
    results: Optional[Dict[str, Any]] = None
    packet: Dict[str, Any] = Field(default_factory=dict)
    moduleArtifacts: Dict[str, Any] = Field(default_factory=dict)
    audit: Optional[Dict[str, Any]] = None
    reviewOverrides: Dict[str, Any] = Field(default_factory=dict)
    notes: str = ""


class ScenarioComparisonRequest(BaseModel):
    inputs: DecisionInputs = Field(default_factory=DecisionInputs)
    results: Optional[Dict[str, Any]] = None
    packet: Dict[str, Any] = Field(default_factory=dict)
    scenarios: List[Dict[str, Any]] = Field(default_factory=list)
    audit: Optional[Dict[str, Any]] = None
    notes: str = ""


class WorkbenchHandoffRequest(BaseModel):
    inputs: DecisionInputs = Field(default_factory=DecisionInputs)
    results: Optional[Dict[str, Any]] = None
    packet: Dict[str, Any] = Field(default_factory=dict)
    readiness: Optional[Dict[str, Any]] = None
    scenarioComparison: Optional[Dict[str, Any]] = None
    requestedTools: List[str] = Field(default_factory=list)
    notes: str = ""


class SavedDecisionPacketRequest(BaseModel):
    inputs: DecisionInputs = Field(default_factory=DecisionInputs)
    results: Optional[Dict[str, Any]] = None
    packet: Dict[str, Any] = Field(default_factory=dict)
    audit: Optional[Dict[str, Any]] = None
    readiness: Optional[Dict[str, Any]] = None
    scenarioComparison: Optional[Dict[str, Any]] = None
    workbenchHandoff: Optional[Dict[str, Any]] = None
    integratedBrief: Optional[Dict[str, Any]] = None
    title: str = ""
    status: str = "draft"
    notes: str = ""


class ExportBundleRequest(BaseModel):
    inputs: DecisionInputs = Field(default_factory=DecisionInputs)
    results: Optional[Dict[str, Any]] = None
    packet: Dict[str, Any] = Field(default_factory=dict)
    audit: Optional[Dict[str, Any]] = None
    readiness: Optional[Dict[str, Any]] = None
    scenarioComparison: Optional[Dict[str, Any]] = None
    workbenchHandoff: Optional[Dict[str, Any]] = None
    integratedBrief: Optional[Dict[str, Any]] = None
    includeRawArtifacts: bool = True
    exportLabel: str = "Decision Studio Export Bundle"


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def npv(capex: float, annual_savings: float, discount_rate_pct: float, years: int) -> float:
    r = discount_rate_pct / 100
    total = -capex
    for t in range(1, years + 1):
        total += annual_savings / ((1 + r) ** t)
    return total


def analyze(inputs: DecisionInputs) -> Dict[str, Any]:
    penalty = {"Low": 2, "Medium": 8, "High": 15, "Very high": 24}.get(inputs.complexity, 8)
    npv_value = npv(inputs.capex, inputs.annualSavings, inputs.discountRate, inputs.modelYears)
    annual_avoided = inputs.baselineEmissions * (inputs.reductionRate / 100) * (inputs.adoptionRate / 100)
    roi = ((inputs.annualSavings * inputs.modelYears - inputs.capex) / inputs.capex * 100) if inputs.capex > 0 else 0
    payback = inputs.capex / inputs.annualSavings if inputs.annualSavings > 0 else math.inf
    env = clamp(30 + inputs.reductionRate * .45 + inputs.adoptionRate * .22 - penalty * .35)
    social = clamp(56 + inputs.socialBenefit * .18 + inputs.adoptionRate * .08 - penalty * .42)
    econ = clamp(48 + (npv_value / max(inputs.capex, 1)) * 34 + min(20, roi / 6) - penalty * .48)
    gov = clamp(45 + inputs.governanceReadiness * .45 + inputs.dataConfidence * .12 - penalty * .3)
    wsum = max(1, inputs.weightEnv + inputs.weightSocial + inputs.weightEconomic + inputs.weightGovernance)
    weighted = (env * inputs.weightEnv + social * inputs.weightSocial + econ * inputs.weightEconomic + gov * inputs.weightGovernance) / wsum
    risk = clamp(inputs.exposure*.35 + inputs.vulnerability*.35 + inputs.stakeholderSensitivity*.2 - inputs.resilience*.18 - inputs.governanceReadiness*.08 + 20)
    status = "Strong candidate with review" if weighted >= 75 and risk < 55 else "Promising but needs mitigation" if weighted >= 60 else "Needs redesign or stronger evidence"
    scenarios = []
    for label, adopt, reduct, cost, benefit in [("Baseline",0,0,0,0),("Conservative",.75,.75,1.15,.8),("Expected",1,1,1,1),("Ambitious",1.25,1.15,1.05,1.1),("Stress test",.6,.65,1.3,.65)]:
        cap = inputs.capex * cost
        sav = inputs.annualSavings * benefit
        scenarios.append({"label": label, "annual_avoided_tco2e": inputs.baselineEmissions * (inputs.reductionRate*reduct/100) * min(100, inputs.adoptionRate*adopt)/100, "npv": npv(cap, sav, inputs.discountRate, inputs.modelYears), "payback_years": cap/sav if sav>0 else None})
    return {"scores":{"environmental":env,"social":social,"economic":econ,"governance":gov,"weighted":weighted},"finance":{"npv":npv_value,"payback_years":payback if math.isfinite(payback) else None,"roi_percent":roi},"emissions":{"annual_avoided_tco2e":annual_avoided,"total_avoided_tco2e":annual_avoided*inputs.modelYears},"risk":{"risk_score":risk,"risk_level":"High" if risk>=70 else "Medium" if risk>=45 else "Low"},"status":status,"scenarios":scenarios,"warnings":["Educational decision support only. Not professional advice or certification."],"workbench_handoffs":["risk-resilience-impact-matrix","economics-forecasting-and-scenario-tool","environmental-monitoring-qaqc-tool","systems-modeling-tool"]}


def module_integrations() -> List[Dict[str, Any]]:
    """Integrated platform workflow modules exposed to Decision Studio."""
    return [
        {
            "id": "catalyst-canvas",
            "step": 1,
            "phase": "Frame",
            "name": "Catalyst Canvas",
            "label": "Problem framing",
            "url": "/catalyst-canvas/#demo",
            "artifact_key": "framing",
            "decision_packet_section": "decision_framing",
            "summary": "Frame a challenge, define an audience, generate POV and HMW prompts, shape a prototype, design a test plan, and export a structured brief.",
            "use_in_brief": "Decision question, audience, POV, how-might-we prompt, prototype, test plan, and constraints.",
        },
        {
            "id": "catalyst-data",
            "step": 2,
            "phase": "Anchor",
            "name": "Catalyst Data",
            "label": "Data records",
            "url": "/catalyst-data/#demo",
            "artifact_key": "evidence_records",
            "decision_packet_section": "evidence_and_measurement",
            "summary": "Create a traceable measurement record with entity, indicator, source, period, confidence, method notes, review status, and JSON export.",
            "use_in_brief": "Sources, indicators, confidence, method notes, measurement records, and audit trail.",
        },
        {
            "id": "catalyst-analytics-r",
            "step": 3,
            "phase": "Model",
            "name": "Catalyst Analytics R",
            "label": "Scenario analysis",
            "url": "/catalyst-analytics-r/#demo",
            "artifact_key": "scenario_analysis",
            "decision_packet_section": "scenarios",
            "summary": "Explore a simplified sustainable-development scenario with assumptions, capital values, emissions budget, interpretation notes, and export logic.",
            "use_in_brief": "Scenario assumptions, trajectories, sensitivity notes, and model interpretation.",
        },
        {
            "id": "global-impact-catalyst",
            "step": 4,
            "phase": "Measure",
            "name": "Global Impact Catalyst",
            "label": "Impact measurement",
            "url": "/global-impact-catalyst/#demo",
            "artifact_key": "impact_records",
            "decision_packet_section": "impact_measurement",
            "summary": "Create a traceable impact record with initiative, goal, SDG-style theme, indicator, baseline, current value, target, source, and progress notes.",
            "use_in_brief": "Impact indicators, baseline/current/target values, progress notes, SDG-style themes, and confidence.",
        },
        {
            "id": "catalyst-narrative-risk",
            "step": 5,
            "phase": "Review",
            "name": "Narrative Risk",
            "label": "Claim review",
            "url": "/narrative-risk/#demo",
            "artifact_key": "claim_reviews",
            "decision_packet_section": "claim_and_risk_review",
            "summary": "Evaluate a claim by evidence strength, uncertainty, source type, stakeholder pressure, narrative volatility, consequences, and review status.",
            "use_in_brief": "Claim strength, uncertainty, narrative volatility, stakeholder pressure, consequences, and review status.",
        },
        {
            "id": "catalyst-finance",
            "step": 6,
            "phase": "Evaluate",
            "name": "Catalyst Finance",
            "label": "Tradeoff analysis",
            "url": "/catalyst-finance/#demo",
            "artifact_key": "finance_analysis",
            "decision_packet_section": "financial_tradeoffs",
            "summary": "Estimate NPV, ROI, payback, benefit-cost ratio, carbon cost per ton, risk-adjusted score, review flags, and decision notes.",
            "use_in_brief": "NPV, ROI, payback, benefit-cost ratio, carbon cost per ton, finance flags, and tradeoff notes.",
        },
        {
            "id": "catalyst-grit",
            "step": 7,
            "phase": "Sustain",
            "name": "Catalyst Grit",
            "label": "Recovery tracking",
            "url": "/human-systems/catalyst-grit/#demo",
            "artifact_key": "execution_recovery",
            "decision_packet_section": "execution_and_recovery",
            "summary": "Describe a setback, assess pressure, impact, energy, support, clarity, recovery actions, and generate a recovery score and next actions.",
            "use_in_brief": "Implementation pressure, support, clarity, recovery capacity, execution risks, and next actions.",
        },
        {
            "id": "decision-studio",
            "step": 8,
            "phase": "Decide",
            "name": "Decision Studio",
            "label": "Decision support",
            "url": "/platform/decision-studio/",
            "artifact_key": "synthesis",
            "decision_packet_section": "integrated_decision_brief",
            "summary": "Generate a four-pillar sustainability decision brief with assumptions, scenarios, calculator-backed outputs, risks, SDG mapping, and auditable review notes.",
            "use_in_brief": "Integrated four-pillar synthesis, recommendation posture, assumptions, risks, caveats, and audit trail.",
        },
    ]


def decision_packet_template() -> Dict[str, Any]:
    modules = module_integrations()
    return {
        "packet_version": "1.7.1",
        "workflow": "Canvas → Data → Analytics R → Global Impact → Narrative Risk → Finance → Grit → Decision Studio",
        "project": {
            "project_name": "",
            "organization_type": "",
            "sector": "",
            "location": "",
            "time_horizon": "",
            "decision_question": "",
        },
        "decision_framing": {},
        "evidence_and_measurement": {"records": []},
        "scenarios": {"records": []},
        "impact_measurement": {"records": []},
        "claim_and_risk_review": {"records": []},
        "financial_tradeoffs": {},
        "execution_and_recovery": {},
        "four_pillar_scores": {},
        "assumptions": [],
        "risks": [],
        "sources": [],
        "audit_trail": [],
        "audit_and_provenance": audit_provenance_template(),
        "integrated_decision_brief": {},
        "scenario_comparison": {},
        "workbench_handoffs": [],
        "saved_packet": {"saved_at": "", "saved_by": "", "status": "draft", "storage": "browser_or_wordpress"},
        "export_center": {"last_exported_at": "", "available_formats": ["json", "markdown", "html", "audit_json", "readiness_json", "scenario_json", "handoff_json"]},
        "module_slots": [
            {
                "module_id": m["id"],
                "name": m["name"],
                "artifact_key": m["artifact_key"],
                "packet_section": m["decision_packet_section"],
                "status": "empty",
            }
            for m in modules
        ],

    }


def audit_provenance_template() -> Dict[str, Any]:
    """Return the v1.1.1 audit and provenance schema."""
    return {
        "audit_version": "1.7.1",
        "decision_packet_id": "SCDS-DRAFT",
        "created_at": "generated-at-runtime",
        "last_updated_at": "generated-at-runtime",
        "review_status": {
            "status": "draft",
            "prepared_by": "",
            "reviewed_by": "",
            "required_reviews": [
                "data/source review",
                "finance assumptions review",
                "risk and claims review",
                "professional review where regulated or safety-critical",
            ],
            "open_questions": [],
        },
        "module_artifact_ledger": [],
        "source_ledger": [],
        "assumptions_register": [],
        "calculation_trace": [],
        "claim_trace": [],
        "change_log": [],
        "warnings": [
            "Educational decision support only; not certification, assurance, legal, financial, engineering, medical, tax, compliance, or investment advice.",
            "Audit entries are generated from user-provided inputs and imported artifacts; they must be reviewed before operational use.",
        ],
    }


def _nonempty(value: Any) -> bool:
    return value not in (None, "", {}, [])


def generate_audit_provenance(req: AuditProvenanceRequest) -> Dict[str, Any]:
    """Generate a structured audit/provenance appendix from inputs, results, packet, and artifacts."""
    inputs = req.inputs
    results = req.results or analyze(inputs)
    artifacts = req.moduleArtifacts or {}
    packet = req.packet or {}
    modules = module_integrations()

    module_ledger = []
    for module in modules:
        key = module["artifact_key"]
        section_key = module.get("decision_packet_section", key)
        artifact = artifacts.get(key) or packet.get(key) or packet.get(section_key)
        present = _nonempty(artifact)
        module_ledger.append({
            "module_id": module["id"],
            "module_name": module["name"],
            "artifact_key": key,
            "packet_section": section_key,
            "status": "attached" if present else "missing",
            "used_in_brief": module.get("use_in_brief", module.get("summary", "")),
            "artifact_snapshot": artifact if present else None,
        })

    source_ledger = []
    # Prefer explicit packet sources/evidence records, then create a fallback source ledger from core inputs.
    for source in packet.get("sources", []) if isinstance(packet.get("sources", []), list) else []:
        if isinstance(source, dict):
            source_ledger.append(source)
    evidence = packet.get("evidence_and_measurement", {}).get("records", []) if isinstance(packet.get("evidence_and_measurement", {}), dict) else []
    for record in evidence if isinstance(evidence, list) else []:
        if isinstance(record, dict):
            source_ledger.append({
                "source_title": record.get("source") or record.get("source_title") or "Catalyst Data record",
                "source_type": record.get("source_type", "measurement record"),
                "confidence": record.get("confidence", record.get("confidence_level", "unspecified")),
                "used_for": record.get("indicator", "evidence and measurement"),
                "method_notes": record.get("method_notes", ""),
            })
    if not source_ledger:
        source_ledger.append({
            "source_title": "User-provided Decision Studio inputs",
            "source_type": "manual input",
            "confidence": inputs.dataConfidence,
            "used_for": "baseline calculations, scoring, finance, and risk screen",
            "method_notes": "Replace or supplement with Catalyst Data records before relying on the brief.",
        })

    assumptions_register = [
        {"assumption": "Baseline emissions", "value": inputs.baselineEmissions, "unit": "tCO2e/year", "module_or_source": "Decision Studio input", "used_in": "emissions reduction calculation", "sensitivity": "high", "review_status": "needs verification"},
        {"assumption": "Reduction rate", "value": inputs.reductionRate, "unit": "%", "module_or_source": "Decision Studio input", "used_in": "emissions reduction calculation", "sensitivity": "high", "review_status": "needs verification"},
        {"assumption": "Adoption rate", "value": inputs.adoptionRate, "unit": "%", "module_or_source": "Decision Studio input", "used_in": "emissions and scenario calculations", "sensitivity": "high", "review_status": "needs verification"},
        {"assumption": "CAPEX", "value": inputs.capex, "unit": "currency", "module_or_source": "Decision Studio / Catalyst Finance", "used_in": "NPV, ROI, payback", "sensitivity": "high", "review_status": "needs finance review"},
        {"assumption": "Annual savings", "value": inputs.annualSavings, "unit": "currency/year", "module_or_source": "Decision Studio / Catalyst Finance", "used_in": "NPV, ROI, payback", "sensitivity": "high", "review_status": "needs finance review"},
        {"assumption": "Discount rate", "value": inputs.discountRate, "unit": "%", "module_or_source": "Decision Studio / Catalyst Finance", "used_in": "NPV", "sensitivity": "medium", "review_status": "needs finance review"},
        {"assumption": "Model years", "value": inputs.modelYears, "unit": "years", "module_or_source": "Decision Studio input", "used_in": "NPV and total avoided emissions", "sensitivity": "medium", "review_status": "needs review"},
    ]

    calculation_trace = [
        {"calculation": "Annual avoided emissions", "formula": "baseline_emissions × reduction_rate × adoption_rate", "inputs": {"baselineEmissions": inputs.baselineEmissions, "reductionRate": inputs.reductionRate, "adoptionRate": inputs.adoptionRate}, "result": results.get("emissions", {}).get("annual_avoided_tco2e"), "unit": "tCO2e/year", "validation_status": "requires source review"},
        {"calculation": "Total avoided emissions", "formula": "annual_avoided × model_years", "inputs": {"modelYears": inputs.modelYears}, "result": results.get("emissions", {}).get("total_avoided_tco2e"), "unit": "tCO2e", "validation_status": "requires boundary review"},
        {"calculation": "NPV", "formula": "-capex + Σ annual_savings/(1+r)^t", "inputs": {"capex": inputs.capex, "annualSavings": inputs.annualSavings, "discountRate": inputs.discountRate, "modelYears": inputs.modelYears}, "result": results.get("finance", {}).get("npv"), "unit": "currency", "validation_status": "requires finance review"},
        {"calculation": "ROI", "formula": "((annual_savings × years - capex) / capex) × 100", "inputs": {"capex": inputs.capex, "annualSavings": inputs.annualSavings, "modelYears": inputs.modelYears}, "result": results.get("finance", {}).get("roi_percent"), "unit": "%", "validation_status": "requires finance review"},
        {"calculation": "Four-pillar weighted score", "formula": "weighted average of environmental, social, economic, governance scores", "inputs": {"weightEnv": inputs.weightEnv, "weightSocial": inputs.weightSocial, "weightEconomic": inputs.weightEconomic, "weightGovernance": inputs.weightGovernance}, "result": results.get("scores", {}).get("weighted"), "unit": "0-100 score", "validation_status": "decision-support screen only"},
        {"calculation": "Risk score", "formula": "exposure + vulnerability + stakeholder sensitivity - resilience - governance readiness adjustment", "inputs": {"exposure": inputs.exposure, "vulnerability": inputs.vulnerability, "stakeholderSensitivity": inputs.stakeholderSensitivity, "resilience": inputs.resilience, "governanceReadiness": inputs.governanceReadiness}, "result": results.get("risk", {}).get("risk_score"), "unit": "0-100 score", "validation_status": "decision-support screen only"},
    ]

    claim_trace = []
    claim_artifacts = artifacts.get("claim_reviews") or packet.get("claim_reviews") or packet.get("claim_and_risk_review", {}).get("records", []) if isinstance(packet.get("claim_and_risk_review", {}), dict) else []
    if isinstance(claim_artifacts, dict):
        claim_artifacts = [claim_artifacts]
    for item in claim_artifacts if isinstance(claim_artifacts, list) else []:
        if isinstance(item, dict):
            claim_trace.append({
                "claim": item.get("claim", item.get("title", "Imported claim review")),
                "evidence_strength": item.get("evidence_strength", item.get("evidenceStrength", "unspecified")),
                "uncertainty": item.get("uncertainty", "unspecified"),
                "source_basis": item.get("source", item.get("source_type", "unspecified")),
                "review_status": item.get("review_status", item.get("reviewStatus", "needs review")),
            })
    if not claim_trace:
        claim_trace.append({
            "claim": f"{inputs.projectName} can proceed under the current decision posture.",
            "evidence_strength": "screening-level only",
            "uncertainty": "medium to high until module artifacts are imported",
            "source_basis": "Decision Studio inputs and deterministic model",
            "review_status": "needs Narrative Risk review",
        })

    audit = audit_provenance_template()
    audit.update({
        "decision_packet_id": packet.get("decision_packet_id", "SCDS-DRAFT"),
        "review_status": {
            **audit["review_status"],
            "status": req.reviewStatus or "draft",
            "prepared_by": req.preparedBy,
            "reviewed_by": req.reviewedBy,
            "open_questions": [
                "Which imported artifacts are missing or incomplete?",
                "Which assumptions have high sensitivity?",
                "Which sources require verification?",
                "Which professional reviews are required before action?",
            ],
        },
        "module_artifact_ledger": module_ledger,
        "source_ledger": source_ledger,
        "assumptions_register": assumptions_register,
        "calculation_trace": calculation_trace,
        "claim_trace": claim_trace,
        "change_log": packet.get("change_log", [{"event": "Audit generated", "detail": "Audit appendix generated from current Decision Studio inputs and artifacts.", "version": APP_VERSION}]),
    })

    completeness = round(100 * sum(1 for row in module_ledger if row["status"] == "attached") / max(1, len(module_ledger)), 1)
    return {
        "ok": True,
        "version": APP_VERSION,
        "audit": audit,
        "audit_summary": {
            "module_artifact_completeness_percent": completeness,
            "sources_count": len(source_ledger),
            "assumptions_count": len(assumptions_register),
            "calculation_trace_count": len(calculation_trace),
            "claim_trace_count": len(claim_trace),
            "review_status": audit["review_status"]["status"],
            "high_priority_reviews": [
                "Verify source records and data confidence.",
                "Review high-sensitivity financial assumptions.",
                "Attach Narrative Risk claim review before external use.",
                "Use professional review for regulated or safety-critical decisions.",
            ],
        },
    }



def artifact_adapter_catalog() -> List[Dict[str, Any]]:
    """Artifact adapters that normalize module JSON exports into the Decision Packet."""
    return [
        {
            "module_id": "catalyst-canvas",
            "name": "Catalyst Canvas",
            "artifact_key": "framing",
            "packet_section": "decision_framing",
            "detects": ["challenge", "audience", "point_of_view", "how_might_we", "prototype", "test_plan"],
            "required_or_expected": ["challenge", "audience", "goal", "constraint", "point_of_view", "how_might_we", "prototype", "test_plan"],
            "summary": "Normalizes challenge framing, audience, POV, HMW prompts, prototype, test plan, assumptions, and review questions.",
        },
        {
            "module_id": "catalyst-data",
            "name": "Catalyst Data",
            "artifact_key": "evidence_records",
            "packet_section": "evidence_and_measurement.records",
            "detects": ["entity", "indicator", "period", "values", "source", "confidence", "trace_path"],
            "required_or_expected": ["entity", "indicator", "period", "values", "source", "confidence", "review_status"],
            "summary": "Normalizes traceable measurement records and source ledger entries.",
        },
        {
            "module_id": "catalyst-analytics-r",
            "name": "Catalyst Analytics R",
            "artifact_key": "scenario_analysis",
            "packet_section": "scenarios.records",
            "detects": ["demo", "inputs", "final", "composite_score", "budget_ratio", "trajectory"],
            "required_or_expected": ["inputs", "final", "composite_score", "budget_ratio", "interpretation_notes"],
            "summary": "Normalizes scenario assumptions, final values, composite score, budget ratio, interpretation notes, and trajectory data.",
        },
        {
            "module_id": "global-impact-catalyst",
            "name": "Global Impact Catalyst",
            "artifact_key": "impact_records",
            "packet_section": "impact_measurement.records",
            "detects": ["record_type", "initiative", "goal", "sdg_theme", "indicator", "baseline_value", "current_value", "target_value"],
            "required_or_expected": ["initiative", "goal", "indicator", "baseline_value", "current_value", "target_value", "source"],
            "summary": "Normalizes impact records, progress-to-target fields, SDG-style themes, confidence, and source details.",
        },
        {
            "module_id": "catalyst-narrative-risk",
            "name": "Narrative Risk",
            "artifact_key": "claim_reviews",
            "packet_section": "claim_and_risk_review.records",
            "detects": ["claim", "risk_score", "risk_level", "components", "flags", "review_actions"],
            "required_or_expected": ["claim", "risk_score", "risk_level", "flags", "review_actions", "decision_note"],
            "summary": "Normalizes claim review, evidence/uncertainty fields, flags, review actions, and narrative risk scoring.",
        },
        {
            "module_id": "catalyst-finance",
            "name": "Catalyst Finance",
            "artifact_key": "finance_analysis",
            "packet_section": "financial_tradeoffs",
            "detects": ["project", "inputs", "results", "interpretation", "npv", "payback_years", "benefit_cost_ratio"],
            "required_or_expected": ["project", "inputs", "results", "interpretation"],
            "summary": "Normalizes NPV, ROI, payback, benefit-cost ratio, carbon cost, risk-adjusted score, and finance review flags.",
        },
        {
            "module_id": "catalyst-grit",
            "name": "Catalyst Grit",
            "artifact_key": "execution_recovery",
            "packet_section": "execution_and_recovery",
            "detects": ["challenge", "impact_severity", "pressure_level", "energy_level", "support_level", "clarity_level", "recovery_score"],
            "required_or_expected": ["challenge", "domain", "impact_severity", "pressure_level", "energy_level", "support_level", "clarity_level", "recovery_actions"],
            "summary": "Normalizes recovery risk, pressure, support, clarity, recovery actions, next actions, and execution capacity.",
        },
        {
            "module_id": "workbench",
            "name": "Sustainable Catalyst Workbench",
            "artifact_key": "workbench_calculations",
            "packet_section": "calculation_trace",
            "detects": ["calculation", "formula", "inputs", "results", "assumptions", "validation_checks", "report"],
            "required_or_expected": ["formula", "inputs", "results"],
            "summary": "Normalizes calculator outputs, formulas, inputs, results, assumptions, validation checks, warnings, and report metadata.",
        },
    ]


def _adapter_by_id(module_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not module_id:
        return None
    normalized = module_id.strip().lower().replace("_", "-")
    aliases = {
        "canvas": "catalyst-canvas",
        "data": "catalyst-data",
        "analytics-r": "catalyst-analytics-r",
        "catalystanalyticsr": "catalyst-analytics-r",
        "impact": "global-impact-catalyst",
        "global-impact": "global-impact-catalyst",
        "narrative-risk": "catalyst-narrative-risk",
        "finance": "catalyst-finance",
        "grit": "catalyst-grit",
        "engineering": "workbench",
        "calculation": "workbench",
    }
    normalized = aliases.get(normalized, normalized)
    for adapter in artifact_adapter_catalog():
        if adapter["module_id"] == normalized or adapter["artifact_key"] == normalized:
            return adapter
    return None


def detect_artifact_adapter(artifact: Dict[str, Any], module_id: Optional[str] = None) -> Dict[str, Any]:
    explicit = _adapter_by_id(module_id)
    if explicit:
        return explicit
    if not isinstance(artifact, dict):
        return artifact_adapter_catalog()[0]
    record_type = str(artifact.get("record_type", "")).lower()
    if record_type == "global_impact_catalyst_record":
        return _adapter_by_id("global-impact-catalyst")
    if record_type == "catalyst_narrative_risk_record":
        return _adapter_by_id("catalyst-narrative-risk")
    if record_type == "catalyst_grit_record":
        return _adapter_by_id("catalyst-grit")
    keys = set(artifact.keys())
    if {"point_of_view", "how_might_we"} & keys or {"challenge", "audience", "prototype", "test_plan"}.issubset(keys):
        return _adapter_by_id("catalyst-canvas")
    if {"entity", "indicator", "period", "values", "source"}.issubset(keys):
        return _adapter_by_id("catalyst-data")
    if {"demo", "final", "composite_score", "budget_ratio"}.issubset(keys) or ("trajectory" in keys and "inputs" in keys):
        return _adapter_by_id("catalyst-analytics-r")
    if {"initiative", "goal", "baseline_value", "current_value", "target_value"}.issubset(keys):
        return _adapter_by_id("global-impact-catalyst")
    if {"claim", "risk_score", "risk_level"}.issubset(keys):
        return _adapter_by_id("catalyst-narrative-risk")
    if {"project", "inputs", "results", "interpretation"}.issubset(keys):
        return _adapter_by_id("catalyst-finance")
    if {"impact_severity", "pressure_level", "recovery_actions"}.issubset(keys) or {"recovery_score", "resilience_state"}.issubset(keys):
        return _adapter_by_id("catalyst-grit")
    if {"formula", "inputs", "results"}.issubset(keys) or "calculation_trace" in keys or "validation_checks" in keys:
        return _adapter_by_id("workbench")
    return _adapter_by_id("workbench") or artifact_adapter_catalog()[-1]


def _dig(data: Dict[str, Any], *path: str, default: Any = None) -> Any:
    cur: Any = data
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def _list(value: Any) -> List[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _source_entry(title: str, source_type: str, confidence: Any, used_for: str, method_notes: str = "") -> Dict[str, Any]:
    return {"source_title": title or "Unspecified source", "source_type": source_type or "unspecified", "confidence": confidence if confidence not in (None, "") else "unspecified", "used_for": used_for, "method_notes": method_notes or ""}


def _assumption(text: str, value: Any, source: str, used_in: str, sensitivity: str = "medium", review_status: str = "needs review") -> Dict[str, Any]:
    return {"assumption": text, "value": value, "module_or_source": source, "used_in": used_in, "sensitivity": sensitivity, "review_status": review_status}


def _merge_list(existing: Any, additions: List[Any]) -> List[Any]:
    base = existing if isinstance(existing, list) else ([] if existing in (None, {}, "") else [existing])
    return base + [x for x in additions if x not in base]


def _apply_packet_patch(packet: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = json.loads(json.dumps(packet or {}))
    if not out:
        out = decision_packet_template()
    for key, value in patch.items():
        if key in {"assumptions", "risks", "sources", "audit_trail", "calculation_trace", "claim_reviews", "workbench_calculations"}:
            out[key] = _merge_list(out.get(key), _list(value))
        elif key == "evidence_and_measurement":
            cur = out.get(key) if isinstance(out.get(key), dict) else {"records": []}
            cur["records"] = _merge_list(cur.get("records"), _list(value.get("records", []))) if isinstance(value, dict) else _merge_list(cur.get("records"), _list(value))
            out[key] = cur
        elif key == "scenarios":
            cur = out.get(key) if isinstance(out.get(key), dict) else {"records": []}
            cur["records"] = _merge_list(cur.get("records"), _list(value.get("records", []))) if isinstance(value, dict) else _merge_list(cur.get("records"), _list(value))
            out[key] = cur
        elif key == "impact_measurement":
            cur = out.get(key) if isinstance(out.get(key), dict) else {"records": []}
            cur["records"] = _merge_list(cur.get("records"), _list(value.get("records", []))) if isinstance(value, dict) else _merge_list(cur.get("records"), _list(value))
            out[key] = cur
        elif key == "claim_and_risk_review":
            cur = out.get(key) if isinstance(out.get(key), dict) else {"records": []}
            cur["records"] = _merge_list(cur.get("records"), _list(value.get("records", []))) if isinstance(value, dict) else _merge_list(cur.get("records"), _list(value))
            out[key] = cur
        elif isinstance(value, dict) and isinstance(out.get(key), dict):
            merged = out.get(key, {}).copy()
            merged.update(value)
            out[key] = merged
        else:
            out[key] = value
    # refresh module slot statuses
    slots = []
    for module in module_integrations():
        key = module["artifact_key"]
        section = module["decision_packet_section"]
        candidate = out.get(key) or out.get(section)
        if section == "evidence_and_measurement" and isinstance(out.get(section), dict):
            candidate = out[section].get("records")
        if section == "scenarios" and isinstance(out.get(section), dict):
            candidate = out[section].get("records")
        if section == "impact_measurement" and isinstance(out.get(section), dict):
            candidate = out[section].get("records")
        if section == "claim_and_risk_review" and isinstance(out.get(section), dict):
            candidate = out[section].get("records")
        slots.append({"module_id": module["id"], "name": module["name"], "artifact_key": key, "packet_section": section, "status": "attached" if _nonempty(candidate) else "empty"})
    # Workbench is an external adapter, not part of the 8-step workflow, but track it when present.
    if _nonempty(out.get("workbench_calculations")) or _nonempty(out.get("calculation_trace")):
        slots.append({"module_id": "workbench", "name": "Sustainable Catalyst Workbench", "artifact_key": "workbench_calculations", "packet_section": "calculation_trace", "status": "attached"})
    out["module_slots"] = slots
    return out


def normalize_artifact(artifact: Dict[str, Any], module_id: Optional[str] = None, preserve_raw: bool = True) -> Dict[str, Any]:
    adapter = detect_artifact_adapter(artifact, module_id)
    mid = adapter["module_id"]
    name = adapter["name"]
    patch: Dict[str, Any] = {"audit_trail": [{"event": "Artifact imported", "module": name, "module_id": mid, "version": APP_VERSION}]}
    summary: Dict[str, Any] = {"module_id": mid, "module_name": name, "artifact_key": adapter["artifact_key"], "packet_section": adapter["packet_section"], "status": "normalized"}
    warnings: List[str] = []
    missing = [k for k in adapter.get("required_or_expected", []) if k not in artifact]
    if missing:
        warnings.append("Missing or not detected fields: " + ", ".join(missing))
    if mid == "catalyst-canvas":
        framing = {
            "challenge": artifact.get("challenge", ""),
            "audience": artifact.get("audience", ""),
            "goal": artifact.get("goal", ""),
            "constraint": artifact.get("constraint", ""),
            "framework": artifact.get("framework", ""),
            "persona": artifact.get("persona", {}),
            "point_of_view": artifact.get("point_of_view", artifact.get("pov", "")),
            "how_might_we": _list(artifact.get("how_might_we")),
            "prototype": artifact.get("prototype", {}),
            "test_plan": artifact.get("test_plan", {}),
            "review_questions": _list(artifact.get("review_questions")),
        }
        patch.update({"decision_framing": framing, "framing": framing, "assumptions": [_assumption(a, None, name, "problem framing", "medium") for a in _list(artifact.get("assumptions"))]})
        if artifact.get("challenge"):
            patch["project"] = {"decision_question": artifact.get("challenge")}
        summary.update({"title": artifact.get("challenge") or artifact.get("goal") or "Canvas framing", "fields_mapped": list(framing.keys())})
    elif mid == "catalyst-data":
        record = {
            "entity": artifact.get("entity", {}),
            "indicator": artifact.get("indicator", {}),
            "period": artifact.get("period", ""),
            "values": artifact.get("values", {}),
            "source": artifact.get("source", {}),
            "confidence": artifact.get("confidence"),
            "review_status": artifact.get("review_status", "needs review"),
            "method_notes": artifact.get("method_notes", ""),
            "trace_path": _list(artifact.get("trace_path")),
        }
        source = artifact.get("source", {}) if isinstance(artifact.get("source"), dict) else {"name": artifact.get("source"), "type": "source"}
        patch.update({"evidence_and_measurement": {"records": [record]}, "evidence_records": [record], "sources": [_source_entry(source.get("name", "Catalyst Data source"), source.get("type", "measurement source"), artifact.get("confidence"), _dig(artifact, "indicator", "name", default="measurement record"), artifact.get("method_notes", ""))]})
        summary.update({"title": _dig(artifact, "indicator", "name", default="Catalyst Data record"), "confidence": artifact.get("confidence"), "review_status": artifact.get("review_status")})
    elif mid == "catalyst-analytics-r":
        scenario = {
            "scenario_name": _dig(artifact, "inputs", "scenarioName", default=artifact.get("demo", "Catalyst Analytics R scenario")),
            "inputs": artifact.get("inputs", {}),
            "final": artifact.get("final", {}),
            "composite_score": artifact.get("composite_score"),
            "budget_ratio": artifact.get("budget_ratio"),
            "interpretation_notes": _list(artifact.get("interpretation_notes")),
            "trajectory": _list(artifact.get("trajectory")),
        }
        assumptions = [_assumption(k, v, name, "scenario analysis", "medium") for k, v in (artifact.get("inputs", {}) if isinstance(artifact.get("inputs"), dict) else {}).items()]
        patch.update({"scenarios": {"records": [scenario]}, "scenario_analysis": scenario, "assumptions": assumptions})
        summary.update({"title": scenario["scenario_name"], "composite_score": artifact.get("composite_score"), "budget_ratio": artifact.get("budget_ratio")})
    elif mid == "global-impact-catalyst":
        record = {
            "initiative": artifact.get("initiative", ""),
            "goal": artifact.get("goal", ""),
            "sdg_theme": artifact.get("sdg_theme", ""),
            "indicator": artifact.get("indicator", ""),
            "unit": artifact.get("unit", ""),
            "baseline_value": artifact.get("baseline_value"),
            "current_value": artifact.get("current_value"),
            "target_value": artifact.get("target_value"),
            "metrics": artifact.get("metrics", {}),
            "confidence": artifact.get("confidence", "unspecified"),
            "review_status": artifact.get("review_status", "needs review"),
            "interpretation_notes": _list(artifact.get("interpretation_notes")),
            "boundaries": _list(artifact.get("boundaries")),
        }
        patch.update({"impact_measurement": {"records": [record]}, "impact_records": [record], "sources": [_source_entry(artifact.get("source", "Global Impact source"), "impact source", artifact.get("confidence"), artifact.get("indicator", "impact indicator"), artifact.get("method_notes", ""))]})
        summary.update({"title": artifact.get("initiative") or artifact.get("indicator") or "Global Impact record", "progress_to_target_percent": _dig(artifact, "metrics", "progress_to_target_percent"), "review_status": artifact.get("review_status")})
    elif mid == "catalyst-narrative-risk":
        record = {
            "claim": artifact.get("claim", ""),
            "risk_score": artifact.get("risk_score"),
            "risk_level": artifact.get("risk_level"),
            "components": artifact.get("components", {}),
            "flags": _list(artifact.get("flags")),
            "review_actions": _list(artifact.get("review_actions")),
            "decision_note": artifact.get("decision_note", ""),
            "inputs": artifact.get("inputs", {}),
        }
        patch.update({"claim_and_risk_review": {"records": [record]}, "claim_reviews": [record], "risks": [{"risk": artifact.get("claim", "Narrative/claim risk"), "score": artifact.get("risk_score"), "level": artifact.get("risk_level"), "module_or_source": name, "flags": _list(artifact.get("flags"))}]})
        summary.update({"title": artifact.get("claim") or "Narrative Risk record", "risk_score": artifact.get("risk_score"), "risk_level": artifact.get("risk_level")})
    elif mid == "catalyst-finance":
        results = artifact.get("results", {}) if isinstance(artifact.get("results"), dict) else artifact
        finance = {
            "project": artifact.get("project", {}),
            "inputs": artifact.get("inputs", {}),
            "results": results,
            "interpretation": artifact.get("interpretation", {}),
            "metadata": artifact.get("metadata", {}),
        }
        calcs = []
        for label, key, unit in [("NPV", "npv", "currency"), ("ROI", "roi_percent", "%"), ("Payback", "payback_years", "years"), ("Benefit-cost ratio", "benefit_cost_ratio", "ratio"), ("Carbon cost per ton", "carbon_cost_per_ton", "currency/tCO2e")]:
            if key in results:
                calcs.append({"calculation": label, "formula": "Catalyst Finance scenario engine", "result": results.get(key), "unit": unit, "validation_status": "requires finance review"})
        patch.update({"financial_tradeoffs": finance, "finance_analysis": finance, "calculation_trace": calcs, "assumptions": [_assumption(k, v, name, "finance analysis", "high" if k in {"capital_cost", "annual_savings", "discount_rate_percent"} else "medium", "needs finance review") for k, v in (artifact.get("inputs", {}) if isinstance(artifact.get("inputs"), dict) else {}).items()]})
        summary.update({"title": _dig(artifact, "project", "name", default="Catalyst Finance analysis"), "npv": results.get("npv"), "roi_percent": results.get("roi_percent"), "payback_years": results.get("payback_years"), "risk_adjusted_score": results.get("risk_adjusted_score")})
    elif mid == "catalyst-grit":
        recovery = {
            "challenge": artifact.get("challenge", ""),
            "domain": artifact.get("domain", ""),
            "impact_severity": artifact.get("impact_severity"),
            "pressure_level": artifact.get("pressure_level"),
            "energy_level": artifact.get("energy_level"),
            "support_level": artifact.get("support_level"),
            "clarity_level": artifact.get("clarity_level"),
            "recovery_score": artifact.get("recovery_score"),
            "resilience_state": artifact.get("resilience_state", ""),
            "recovery_actions": _list(artifact.get("recovery_actions")),
            "risk_flags": _list(artifact.get("risk_flags")),
            "next_actions": _list(artifact.get("next_actions")),
            "decision_note": artifact.get("decision_note", ""),
        }
        patch.update({"execution_and_recovery": recovery, "execution_recovery": recovery, "risks": [{"risk": "Execution/recovery risk", "score": artifact.get("recovery_score"), "level": artifact.get("resilience_state"), "module_or_source": name, "flags": _list(artifact.get("risk_flags"))}]})
        summary.update({"title": artifact.get("challenge") or "Catalyst Grit recovery record", "recovery_score": artifact.get("recovery_score"), "resilience_state": artifact.get("resilience_state")})
    else:
        calc = {
            "calculation": artifact.get("calculation", artifact.get("title", "Workbench calculation")),
            "formula": artifact.get("formula", ""),
            "inputs": artifact.get("inputs", {}),
            "results": artifact.get("results", artifact.get("result")),
            "assumptions": artifact.get("assumptions", []),
            "validation_checks": artifact.get("validation_checks", artifact.get("checks", [])),
            "warnings": artifact.get("warnings", []),
            "report": artifact.get("report", {}),
        }
        patch.update({"workbench_calculations": [calc], "calculation_trace": [{"calculation": calc["calculation"], "formula": calc["formula"], "inputs": calc["inputs"], "result": calc["results"], "unit": artifact.get("unit", ""), "validation_status": "imported from Workbench"}]})
        summary.update({"title": calc["calculation"], "formula": calc["formula"]})
    if preserve_raw:
        patch.setdefault("module_artifacts_raw", {})[adapter["artifact_key"]] = artifact
    return {"ok": True, "version": APP_VERSION, "adapter": adapter, "summary": summary, "packet_patch": patch, "warnings": warnings, "artifact": artifact}


def import_artifact_into_packet(artifact: Dict[str, Any], module_id: Optional[str] = None, packet: Optional[Dict[str, Any]] = None, preserve_raw: bool = True) -> Dict[str, Any]:
    normalized = normalize_artifact(artifact, module_id=module_id, preserve_raw=preserve_raw)
    updated_packet = _apply_packet_patch(packet or decision_packet_template(), normalized["packet_patch"])
    analysis = synthesize_decision_packet(updated_packet, None)
    return {"ok": True, "version": APP_VERSION, "import_result": normalized, "decision_packet": updated_packet, "analysis": analysis}


def synthesize_decision_packet(packet: Dict[str, Any], inputs: Optional[DecisionInputs] = None) -> Dict[str, Any]:
    packet = packet or decision_packet_template()
    modules = module_integrations()
    filled = []
    missing = []
    for module in modules:
        key = module["artifact_key"]
        section = module["decision_packet_section"]
        value = packet.get(key) or packet.get(section)
        if section in {"evidence_and_measurement", "scenarios", "impact_measurement", "claim_and_risk_review"} and isinstance(packet.get(section), dict):
            value = packet[section].get("records", [])
        if _nonempty(value):
            filled.append(module["id"])
        else:
            missing.append(module["id"])
    workbench_attached = _nonempty(packet.get("workbench_calculations")) or _nonempty(packet.get("calculation_trace"))
    base_results = analyze(inputs or DecisionInputs())
    readiness = round((len(filled) / max(1, len(modules))) * 100, 1)
    source_count = len(packet.get("sources", [])) if isinstance(packet.get("sources", []), list) else 0
    assumption_count = len(packet.get("assumptions", [])) if isinstance(packet.get("assumptions", []), list) else 0
    calculation_count = len(packet.get("calculation_trace", [])) if isinstance(packet.get("calculation_trace", []), list) else 0
    review_flags = []
    if "catalyst-data" in missing:
        review_flags.append("Evidence records are missing; import Catalyst Data before external use.")
    if "catalyst-finance" in missing:
        review_flags.append("Finance artifact is missing; import Catalyst Finance before relying on tradeoff metrics.")
    if "catalyst-narrative-risk" in missing:
        review_flags.append("Narrative Risk artifact is missing; import claim review before publishing claims.")
    if source_count == 0:
        review_flags.append("No explicit source ledger entries are attached yet.")
    return {
        "ok": True,
        "version": APP_VERSION,
        "decision_packet_version": "1.7.1",
        "workflow_readiness_percent": readiness,
        "filled_modules": filled,
        "missing_modules": missing,
        "module_count": len(modules),
        "workbench_attached": workbench_attached,
        "packet_quality": {
            "source_count": source_count,
            "assumption_count": assumption_count,
            "calculation_trace_count": calculation_count,
            "review_flags": review_flags,
        },
        "brief_readiness": compute_brief_readiness(packet, inputs or DecisionInputs(), base_results, packet.get("audit_and_provenance") if isinstance(packet.get("audit_and_provenance"), dict) else None),
        "synthesis": {
            "posture": base_results["status"],
            "weighted_score": base_results["scores"]["weighted"],
            "risk_level": base_results["risk"]["risk_level"],
            "risk_score": base_results["risk"]["risk_score"],
            "next_best_steps": [
                "Import Canvas framing before finalizing the decision question.",
                "Attach Catalyst Data records for each major claim and calculation.",
                "Import Finance, Narrative Risk, and Grit artifacts before treating the brief as decision-ready.",
                "Use Workbench handoffs for any calculation requiring deeper symbolic, graph, engineering, or domain-specific review.",
            ],
        },
        "warnings": [
            "Module Artifact Adapters normalize user-provided JSON exports. They do not verify truth, source quality, professional compliance, or certification status.",
            "Decision Packet readiness is a review workflow aid, not approval, assurance, legal advice, financial advice, engineering review, ESG/SDG certification, or professional signoff.",
        ],
    }



def review_status_catalog() -> Dict[str, Any]:
    """Review state vocabulary used by v1.7.1 readiness gates."""
    return {
        "review_version": APP_VERSION,
        "states": [
            {"id": "not_started", "label": "Not started", "meaning": "No usable artifact or section content is present."},
            {"id": "needs_evidence", "label": "Needs evidence", "meaning": "The section has draft content but lacks source, confidence, or measurement support."},
            {"id": "needs_review", "label": "Needs review", "meaning": "The section is usable for a draft brief but requires human review before publication or reliance."},
            {"id": "needs_expert_review", "label": "Needs expert review", "meaning": "The section touches finance, engineering, legal/compliance, claims, safety, or other professional-review areas."},
            {"id": "ready_for_draft", "label": "Ready for draft", "meaning": "The section can support a draft brief with caveats."},
            {"id": "ready_for_export", "label": "Ready for export", "meaning": "The section has artifacts, sources, review status, and no critical unresolved flags."},
        ],
        "export_gate": {
            "draft_minimum": 50,
            "reviewed_export_minimum": 75,
            "professional_reliance": "Requires qualified human review regardless of score.",
        },
    }


def readiness_sections() -> List[Dict[str, Any]]:
    """Section-level readiness model for integrated Decision Packets."""
    return [
        {"id": "framing", "label": "Problem Framing", "module_id": "catalyst-canvas", "weight": 10, "required": True, "expert_review": False},
        {"id": "evidence", "label": "Evidence & Measurement", "module_id": "catalyst-data", "weight": 16, "required": True, "expert_review": False},
        {"id": "scenarios", "label": "Scenario Analysis", "module_id": "catalyst-analytics-r", "weight": 10, "required": False, "expert_review": False},
        {"id": "impact", "label": "Impact Measurement", "module_id": "global-impact-catalyst", "weight": 12, "required": True, "expert_review": False},
        {"id": "claims", "label": "Claim & Narrative Risk", "module_id": "catalyst-narrative-risk", "weight": 12, "required": True, "expert_review": True},
        {"id": "finance", "label": "Financial Tradeoffs", "module_id": "catalyst-finance", "weight": 14, "required": True, "expert_review": True},
        {"id": "recovery", "label": "Execution & Recovery", "module_id": "catalyst-grit", "weight": 8, "required": False, "expert_review": False},
        {"id": "audit", "label": "Audit & Provenance", "module_id": "audit", "weight": 10, "required": True, "expert_review": False},
        {"id": "synthesis", "label": "Integrated Brief", "module_id": "decision-studio", "weight": 8, "required": True, "expert_review": False},
    ]


def _section_value(packet: Dict[str, Any], sid: str, results: Optional[Dict[str, Any]] = None, audit: Optional[Dict[str, Any]] = None) -> Any:
    results = results or {}
    audit = audit or {}
    if sid == "framing":
        return packet.get("decision_framing") or packet.get("framing") or (packet.get("project") or {}).get("decision_question")
    if sid == "evidence":
        records = packet.get("evidence_and_measurement", {}).get("records", []) if isinstance(packet.get("evidence_and_measurement", {}), dict) else []
        return records or packet.get("evidence_records") or packet.get("sources") or audit.get("source_ledger")
    if sid == "scenarios":
        records = packet.get("scenarios", {}).get("records", []) if isinstance(packet.get("scenarios", {}), dict) else []
        return records or packet.get("scenario_analysis") or results.get("scenarios")
    if sid == "impact":
        records = packet.get("impact_measurement", {}).get("records", []) if isinstance(packet.get("impact_measurement", {}), dict) else []
        return records or packet.get("impact_records")
    if sid == "claims":
        records = packet.get("claim_and_risk_review", {}).get("records", []) if isinstance(packet.get("claim_and_risk_review", {}), dict) else []
        return records or packet.get("claim_reviews") or audit.get("claim_trace")
    if sid == "finance":
        return packet.get("financial_tradeoffs") or packet.get("finance_analysis") or results.get("finance")
    if sid == "recovery":
        return packet.get("execution_and_recovery") or packet.get("execution_recovery")
    if sid == "audit":
        return packet.get("audit_and_provenance") or audit or packet.get("audit_trail")
    if sid == "synthesis":
        return packet.get("integrated_decision_brief") or results.get("scores") or results.get("status")
    return None


def _source_count_from(packet: Dict[str, Any], audit: Optional[Dict[str, Any]] = None) -> int:
    audit = audit or {}
    count = 0
    if isinstance(packet.get("sources"), list):
        count += len(packet.get("sources", []))
    if isinstance(audit.get("source_ledger"), list):
        count += len(audit.get("source_ledger", []))
    evidence = packet.get("evidence_and_measurement", {}).get("records", []) if isinstance(packet.get("evidence_and_measurement", {}), dict) else []
    if isinstance(evidence, list):
        count += len(evidence)
    return count


def _review_state(score: float, flags: List[Dict[str, Any]], required: bool, expert_review: bool) -> str:
    has_critical = any(f.get("severity") == "critical" for f in flags)
    has_high = any(f.get("severity") == "high" for f in flags)
    if score <= 0:
        return "not_started"
    if has_critical or (required and score < 40):
        return "needs_evidence"
    if expert_review and (has_high or score < 90):
        return "needs_expert_review"
    if score < 70 or has_high:
        return "needs_review"
    if score < 90:
        return "ready_for_draft"
    return "ready_for_export"


def compute_brief_readiness(packet: Dict[str, Any], inputs: DecisionInputs, results: Optional[Dict[str, Any]] = None, audit: Optional[Dict[str, Any]] = None, review_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Compute section-level readiness, review states, unresolved issues, and export gates."""
    packet = packet or decision_packet_template()
    results = results or analyze(inputs)
    audit = audit or {}
    review_overrides = review_overrides or {}
    sections = []
    unresolved: List[Dict[str, Any]] = []
    total_weight = 0.0
    weighted_score = 0.0
    source_count = _source_count_from(packet, audit)
    assumptions_count = len(packet.get("assumptions", [])) if isinstance(packet.get("assumptions"), list) else 0
    calculation_count = len(packet.get("calculation_trace", [])) if isinstance(packet.get("calculation_trace"), list) else 0
    module_slots = packet.get("module_slots", []) if isinstance(packet.get("module_slots"), list) else []
    attached_modules = {m.get("module_id") for m in module_slots if isinstance(m, dict) and m.get("status") == "attached"}

    for sec in readiness_sections():
        sid = sec["id"]
        value = _section_value(packet, sid, results, audit)
        present = _nonempty(value)
        score = 0.0
        flags: List[Dict[str, Any]] = []
        if present:
            score = 55.0
        if sec["module_id"] in attached_modules:
            score += 20.0
        if sid == "framing":
            framing = packet.get("decision_framing") or packet.get("framing") or {}
            dq = (framing.get("decision_question") or framing.get("challenge") or (packet.get("project") or {}).get("decision_question") or inputs.decisionQuestion) if isinstance(framing, dict) else inputs.decisionQuestion
            if dq:
                score += 20
            else:
                flags.append({"severity": "high", "section": sid, "issue": "Decision question is missing.", "action": "Import Catalyst Canvas or complete the intake decision question."})
        elif sid == "evidence":
            if source_count:
                score += min(25, source_count * 8)
            else:
                flags.append({"severity": "critical", "section": sid, "issue": "No source or evidence records are attached.", "action": "Import Catalyst Data records or add source ledger entries."})
            if float(inputs.dataConfidence or 0) < 60:
                flags.append({"severity": "high", "section": sid, "issue": "Data confidence is below 60.", "action": "Document source quality, method notes, and review status."})
        elif sid == "scenarios":
            if present:
                score += 25
            else:
                score = 35
                flags.append({"severity": "medium", "section": sid, "issue": "No imported scenario artifact is attached.", "action": "Import Catalyst Analytics R or rely on Decision Studio's built-in scenario screen as a draft."})
        elif sid == "impact":
            if present:
                score += 25
            else:
                flags.append({"severity": "high", "section": sid, "issue": "Impact record is missing.", "action": "Import Global Impact Catalyst with baseline, current, target, source, and progress notes."})
        elif sid == "claims":
            if present:
                score += 20
            else:
                flags.append({"severity": "high", "section": sid, "issue": "Claim review is missing.", "action": "Import Narrative Risk before publishing external claims."})
        elif sid == "finance":
            if present:
                score += 15
            if inputs.capex > 0 and inputs.annualSavings > 0:
                score += 15
            else:
                flags.append({"severity": "high", "section": sid, "issue": "Finance assumptions are incomplete.", "action": "Enter CAPEX and annual savings or import Catalyst Finance."})
            if assumptions_count == 0:
                flags.append({"severity": "medium", "section": sid, "issue": "No imported assumptions register is attached.", "action": "Import Catalyst Finance or generate audit/provenance before final export."})
        elif sid == "recovery":
            if present:
                score += 30
            else:
                score = 35
                flags.append({"severity": "medium", "section": sid, "issue": "Execution/recovery artifact is missing.", "action": "Import Catalyst Grit to assess implementation pressure, support, clarity, and recovery actions."})
        elif sid == "audit":
            audit_present = bool(audit) or _nonempty(packet.get("audit_and_provenance")) or _nonempty(packet.get("audit_trail"))
            if audit_present:
                score += 20
            if source_count > 0:
                score += 15
            if assumptions_count > 0 or (audit and audit.get("assumptions_register")):
                score += 15
            if calculation_count > 0 or (audit and audit.get("calculation_trace")):
                score += 15
            if source_count == 0:
                flags.append({"severity": "critical", "section": sid, "issue": "Audit source ledger is incomplete.", "action": "Generate audit/provenance after importing evidence records."})
        elif sid == "synthesis":
            if results.get("scores"):
                score += 25
            if results.get("risk"):
                score += 15
            if results.get("finance"):
                score += 10
            if results.get("emissions"):
                score += 10
        score = clamp(score, 0, 100)
        # Allow explicit review override to raise/lower state without hiding score.
        override = review_overrides.get(sid) if isinstance(review_overrides, dict) else None
        state = str(override.get("state")) if isinstance(override, dict) and override.get("state") else _review_state(score, flags, bool(sec["required"]), bool(sec["expert_review"]))
        for f in flags:
            unresolved.append(f)
        sections.append({
            "id": sid,
            "label": sec["label"],
            "module_id": sec["module_id"],
            "required": bool(sec["required"]),
            "expert_review": bool(sec["expert_review"]),
            "score": round(score, 1),
            "review_state": state,
            "status_label": state.replace("_", " ").title(),
            "present": bool(present),
            "flags": flags,
        })
        total_weight += float(sec["weight"])
        weighted_score += float(sec["weight"]) * score

    readiness_percent = round(weighted_score / max(1.0, total_weight), 1)
    critical_count = sum(1 for f in unresolved if f.get("severity") == "critical")
    high_count = sum(1 for f in unresolved if f.get("severity") == "high")
    required_not_ready = [s for s in sections if s["required"] and s["review_state"] in {"not_started", "needs_evidence"}]
    expert_review_needed = [s for s in sections if s["review_state"] == "needs_expert_review"]
    if critical_count or required_not_ready:
        overall_state = "needs_evidence"
    elif expert_review_needed:
        overall_state = "needs_expert_review"
    elif readiness_percent >= 85 and high_count == 0:
        overall_state = "ready_for_export"
    elif readiness_percent >= 65:
        overall_state = "ready_for_draft"
    else:
        overall_state = "needs_review"
    export_gate = {
        "draft_brief_allowed": readiness_percent >= 50,
        "reviewed_export_allowed": readiness_percent >= 75 and critical_count == 0 and not required_not_ready,
        "professional_reliance_allowed": False,
        "blocking_issues": [f for f in unresolved if f.get("severity") in {"critical", "high"}],
    }
    next_actions = []
    for f in unresolved[:8]:
        next_actions.append(f.get("action", f.get("issue", "Review unresolved issue.")))
    if not next_actions:
        next_actions = ["Generate the integrated brief, export the audit appendix, and complete any applicable expert reviews before operational use."]
    return {
        "ok": True,
        "version": APP_VERSION,
        "readiness_version": APP_VERSION,
        "readiness_percent": readiness_percent,
        "overall_review_state": overall_state,
        "overall_status_label": overall_state.replace("_", " ").title(),
        "sections": sections,
        "unresolved_issues": unresolved,
        "counts": {
            "sources": source_count,
            "assumptions": assumptions_count,
            "calculations": calculation_count,
            "critical_issues": critical_count,
            "high_issues": high_count,
            "sections_ready_for_export": sum(1 for s in sections if s["review_state"] == "ready_for_export"),
            "sections_needing_expert_review": len(expert_review_needed),
        },
        "export_gate": export_gate,
        "required_reviews": [
            "Data/source review" if source_count else "Data/source review required before export",
            "Finance assumptions review",
            "Narrative/claim risk review",
            "Professional review where regulated, safety-critical, financial, legal, engineering, medical, tax, compliance, assurance, or certification use is possible",
        ],
        "next_actions": list(dict.fromkeys(next_actions)),
        "warnings": [
            "Brief readiness is a workflow quality gate, not approval, assurance, certification, or professional signoff.",
            "Professional reliance remains disallowed without qualified human review regardless of readiness score.",
        ],
    }


def generate_brief_readiness(req: BriefReadinessRequest) -> Dict[str, Any]:
    packet = req.packet or decision_packet_template()
    results = req.results or analyze(req.inputs)
    for module_id, artifact in (req.moduleArtifacts or {}).items():
        if isinstance(artifact, dict) and _nonempty(artifact):
            imported = import_artifact_into_packet(artifact, module_id=module_id, packet=packet, preserve_raw=True)
            packet = imported.get("decision_packet", packet)
    audit = req.audit if isinstance(req.audit, dict) and req.audit else {}
    if not audit:
        audit = generate_audit_provenance(AuditProvenanceRequest(inputs=req.inputs, results=results, packet=packet, moduleArtifacts=req.moduleArtifacts)).get("audit", {})
    readiness = compute_brief_readiness(packet, req.inputs, results, audit, req.reviewOverrides)
    return {"ok": True, "version": APP_VERSION, "readiness": readiness, "decision_packet": packet, "results": results, "audit": audit, "review_status_catalog": review_status_catalog()}

def _records_from_packet(packet: Dict[str, Any], section: str, legacy: str = "") -> List[Dict[str, Any]]:
    value = packet.get(section)
    if isinstance(value, dict) and isinstance(value.get("records"), list):
        return [x for x in value.get("records", []) if isinstance(x, dict)]
    if isinstance(value, list):
        return [x for x in value if isinstance(x, dict)]
    if legacy:
        legacy_value = packet.get(legacy)
        if isinstance(legacy_value, list):
            return [x for x in legacy_value if isinstance(x, dict)]
        if isinstance(legacy_value, dict):
            return [legacy_value]
    return []


def _compact_text(value: Any, default: str = "Not specified") -> str:
    if value in (None, "", [], {}):
        return default
    if isinstance(value, (list, tuple)):
        parts = [_compact_text(v, "") for v in value if v not in (None, "", [], {})]
        return "; ".join([p for p in parts if p]) or default
    if isinstance(value, dict):
        for key in ("name", "title", "label", "summary", "description", "value"):
            if value.get(key):
                return str(value.get(key))
        return json.dumps(value, ensure_ascii=False)[:220]
    return str(value)


def _first_present(*values: Any, default: str = "Not specified") -> str:
    for value in values:
        if value not in (None, "", [], {}):
            return _compact_text(value, default)
    return default


def _brief_number(value: Any, suffix: str = "") -> str:
    try:
        num = float(value)
        if abs(num) >= 1000:
            text = f"{num:,.0f}"
        else:
            text = f"{num:.1f}".rstrip("0").rstrip(".")
        return f"{text}{suffix}"
    except Exception:
        return _compact_text(value, "n/a")


def _money_text(value: Any) -> str:
    try:
        return f"${float(value):,.0f}"
    except Exception:
        return _compact_text(value, "n/a")


def integrated_brief_markdown(brief: Dict[str, Any]) -> str:
    def bullets(items: Any) -> str:
        if not isinstance(items, list) or not items:
            return "- None recorded."
        return "\n".join(f"- {_compact_text(item)}" for item in items)

    md = [
        f"# {brief.get('title', 'Integrated Decision Brief')}",
        "",
        f"**Decision Packet:** {brief.get('decision_packet_id', 'SCDS-DRAFT')}",
        f"**Recommendation posture:** {brief.get('recommendation_posture', 'Review required')}",
        f"**Brief readiness:** {brief.get('brief_readiness', {}).get('readiness_percent', 'n/a')}%",
        "",
        "## Executive Summary",
        brief.get('executive_summary', ''),
        "",
        "## Brief Readiness and Review Status",
        f"Overall state: {brief.get('brief_readiness', {}).get('overall_status_label', 'Needs Review')}.",
        bullets([f"{s.get('label')}: {s.get('status_label')} ({s.get('score')}%)" for s in brief.get('brief_readiness', {}).get('section_statuses', [])]),
        "",
        "## Decision Question",
        brief.get('decision_question', 'Not specified'),
        "",
        "## Problem Framing",
        brief.get('problem_framing', {}).get('summary', 'Not specified'),
        "",
        "## Four-Pillar Sustainability Analysis",
        bullets(brief.get('four_pillar_analysis', {}).get('findings', [])),
        "",
        "## Scenario Comparison",
        bullets(brief.get('scenario_comparison', {}).get('findings', [])),
        "",
        "## Financial Tradeoffs",
        bullets(brief.get('financial_tradeoffs', {}).get('findings', [])),
        "",
        "## Impact Measurement",
        bullets(brief.get('impact_measurement', {}).get('findings', [])),
        "",
        "## Claim and Narrative Risk",
        bullets(brief.get('claim_and_narrative_risk', {}).get('findings', [])),
        "",
        "## Execution and Recovery Risk",
        bullets(brief.get('execution_and_recovery', {}).get('findings', [])),
        "",
        "## Assumptions and Uncertainties",
        bullets(brief.get('assumptions_and_uncertainties', {}).get('findings', [])),
        "",
        "## Evidence and Source Ledger",
        bullets(brief.get('evidence_and_source_ledger', {}).get('findings', [])),
        "",
        "## Audit Appendix Summary",
        bullets(brief.get('audit_appendix_summary', {}).get('findings', [])),
        "",
        "## Next Review Actions",
        bullets(brief.get('next_review_actions', [])),
        "",
        "## Boundaries",
        "This is educational decision support only. It is not legal, financial, investment, engineering, medical, tax, compliance, assurance, ESG/SDG certification, or professional advice.",
    ]
    return "\n".join(md).strip() + "\n"


def integrated_brief_html(brief: Dict[str, Any]) -> str:
    def esc_html(x: Any) -> str:
        return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    def ul(items: Any) -> str:
        if not isinstance(items, list) or not items:
            return "<p>None recorded.</p>"
        return "<ul>" + "".join(f"<li>{esc_html(_compact_text(i))}</li>" for i in items) + "</ul>"
    sections = [
        ("Problem Framing", brief.get('problem_framing', {}).get('summary', 'Not specified')),
        ("Four-Pillar Sustainability Analysis", ul(brief.get('four_pillar_analysis', {}).get('findings', []))),
        ("Scenario Comparison", ul(brief.get('scenario_comparison', {}).get('findings', []))),
        ("Financial Tradeoffs", ul(brief.get('financial_tradeoffs', {}).get('findings', []))),
        ("Impact Measurement", ul(brief.get('impact_measurement', {}).get('findings', []))),
        ("Claim and Narrative Risk", ul(brief.get('claim_and_narrative_risk', {}).get('findings', []))),
        ("Execution and Recovery Risk", ul(brief.get('execution_and_recovery', {}).get('findings', []))),
        ("Assumptions and Uncertainties", ul(brief.get('assumptions_and_uncertainties', {}).get('findings', []))),
        ("Evidence and Source Ledger", ul(brief.get('evidence_and_source_ledger', {}).get('findings', []))),
        ("Audit Appendix Summary", ul(brief.get('audit_appendix_summary', {}).get('findings', []))),
        ("Next Review Actions", ul(brief.get('next_review_actions', []))),
    ]
    body = f"<h1>{esc_html(brief.get('title', 'Integrated Decision Brief'))}</h1>"
    body += f"<p><strong>Decision Packet:</strong> {esc_html(brief.get('decision_packet_id', 'SCDS-DRAFT'))}</p>"
    body += f"<p><strong>Recommendation posture:</strong> {esc_html(brief.get('recommendation_posture', 'Review required'))}</p>"
    body += f"<p><strong>Brief readiness:</strong> {esc_html(brief.get('brief_readiness', {}).get('readiness_percent', 'n/a'))}%</p>"
    body += f"<h2>Executive Summary</h2><p>{esc_html(brief.get('executive_summary', ''))}</p>"
    body += f"<h2>Decision Question</h2><p>{esc_html(brief.get('decision_question', 'Not specified'))}</p>"
    for title, content in sections:
        if str(content).startswith("<"):
            body += f"<h2>{esc_html(title)}</h2>{content}"
        else:
            body += f"<h2>{esc_html(title)}</h2><p>{esc_html(content)}</p>"
    body += "<h2>Boundaries</h2><p>This is educational decision support only. It is not legal, financial, investment, engineering, medical, tax, compliance, assurance, ESG/SDG certification, or professional advice.</p>"
    return body


def generate_integrated_brief(req: IntegratedBriefRequest) -> Dict[str, Any]:
    inputs = req.inputs or DecisionInputs()
    results = req.results or analyze(inputs)
    packet = req.packet or decision_packet_template()

    # If moduleArtifacts are provided directly, normalize them into the packet before synthesis.
    for module_id, artifact in (req.moduleArtifacts or {}).items():
        if isinstance(artifact, dict) and _nonempty(artifact):
            imported = import_artifact_into_packet(artifact, module_id=module_id, packet=packet, preserve_raw=True)
            packet = imported.get("decision_packet", packet)

    readiness = synthesize_decision_packet(packet, inputs)
    audit = req.audit if isinstance(req.audit, dict) and req.audit else generate_audit_provenance(AuditProvenanceRequest(inputs=inputs, results=results, packet=packet, moduleArtifacts=req.moduleArtifacts)).get("audit", {})

    framing = packet.get("decision_framing") or packet.get("framing") or {}
    scenarios = _records_from_packet(packet, "scenarios", "scenario_analysis")
    impacts = _records_from_packet(packet, "impact_measurement", "impact_records")
    claims = _records_from_packet(packet, "claim_and_risk_review", "claim_reviews")
    finance = packet.get("financial_tradeoffs") or packet.get("finance_analysis") or {}
    recovery = packet.get("execution_and_recovery") or packet.get("execution_recovery") or {}
    sources = packet.get("sources") if isinstance(packet.get("sources"), list) else []
    assumptions = packet.get("assumptions") if isinstance(packet.get("assumptions"), list) else []
    calc_trace = packet.get("calculation_trace") if isinstance(packet.get("calculation_trace"), list) else []

    scores = results.get("scores", {})
    risk = results.get("risk", {})
    emissions = results.get("emissions", {})
    finance_results = finance.get("results", {}) if isinstance(finance, dict) and isinstance(finance.get("results"), dict) else results.get("finance", {})
    weighted = float(scores.get("weighted", 0) or 0)
    risk_score = float(risk.get("risk_score", 0) or 0)
    posture = "Advance with mitigations" if weighted >= 75 and risk_score < 55 else "Continue due diligence" if weighted >= 60 and risk_score < 70 else "Revise before approval"
    if readiness.get("workflow_readiness_percent", 0) < 50:
        posture += " — incomplete packet"

    decision_question = _first_present(
        framing.get("decision_question") if isinstance(framing, dict) else None,
        inputs.decisionQuestion,
        default="Decision question not specified",
    )
    project_name = _first_present(
        (packet.get("project") or {}).get("project_name") if isinstance(packet.get("project"), dict) else None,
        inputs.projectName,
        default="Decision project",
    )

    scenario_findings = []
    if scenarios:
        for item in scenarios[:4]:
            scenario_findings.append(_first_present(item.get("demo"), item.get("name"), item.get("label"), default="Imported scenario") + ": " + _first_present(item.get("interpretation"), item.get("decision_note"), item.get("summary"), default="Imported scenario artifact attached."))
    else:
        for sc in results.get("scenarios", [])[:5]:
            scenario_findings.append(f"{sc.get('label')}: annual avoided emissions {_brief_number(sc.get('annual_avoided_tco2e'))} tCO2e; NPV {_money_text(sc.get('npv'))}; payback {_brief_number(sc.get('payback_years'), ' years')}.")

    impact_findings = []
    for item in impacts[:5]:
        impact_findings.append(f"{_first_present(item.get('initiative'), item.get('goal'), item.get('indicator'), default='Impact record')}: baseline {_compact_text(item.get('baseline_value', item.get('baseline', 'n/a')))}, current {_compact_text(item.get('current_value', item.get('current', 'n/a')))}, target {_compact_text(item.get('target_value', item.get('target', 'n/a')))}.")
    if not impact_findings:
        impact_findings = ["No Global Impact artifact is attached yet; treat impact claims as draft until baseline, current, target, source, and review status are documented."]

    claim_findings = []
    for item in claims[:5]:
        claim_findings.append(f"{_first_present(item.get('claim'), default='Imported claim')}: risk {_compact_text(item.get('risk_level', 'unspecified'))}, evidence {_compact_text(item.get('evidence_strength', 'unspecified'))}, uncertainty {_compact_text(item.get('uncertainty', 'unspecified'))}.")
    if not claim_findings:
        claim_findings = ["No Narrative Risk artifact is attached yet; external claims should remain provisional until evidence strength, uncertainty, stakeholder pressure, and narrative volatility are reviewed."]

    recovery_findings = []
    if isinstance(recovery, dict) and recovery:
        recovery_findings.append(f"Recovery state: {_first_present(recovery.get('resilience_state'), default='unspecified')}; recovery score {_compact_text(recovery.get('recovery_score', 'n/a'))}.")
        for action in recovery.get("next_actions", [])[:3] if isinstance(recovery.get("next_actions"), list) else []:
            recovery_findings.append("Next action: " + _compact_text(action))
    else:
        recovery_findings = ["No Catalyst Grit recovery artifact is attached yet; execution pressure, support, clarity, energy, and next actions require review."]

    source_findings = []
    for item in sources[:5]:
        if isinstance(item, dict):
            source_findings.append(f"{_first_present(item.get('source_title'), item.get('name'), default='Source')}: confidence {_compact_text(item.get('confidence', 'unspecified'))}; used for {_compact_text(item.get('used_for', 'unspecified'))}.")
    if not source_findings:
        audit_sources = audit.get("source_ledger", []) if isinstance(audit.get("source_ledger"), list) else []
        for item in audit_sources[:5]:
            if isinstance(item, dict):
                source_findings.append(f"{_first_present(item.get('source_title'), default='Source')}: confidence {_compact_text(item.get('confidence', 'unspecified'))}; used for {_compact_text(item.get('used_for', 'unspecified'))}.")
    if not source_findings:
        source_findings = ["No explicit source ledger has been attached; import Catalyst Data records before external reliance."]

    assumption_findings = []
    for item in assumptions[:5]:
        if isinstance(item, dict):
            assumption_findings.append(f"{_first_present(item.get('assumption'), default='Assumption')}: {_compact_text(item.get('value', 'n/a'))}; sensitivity {_compact_text(item.get('sensitivity', 'unspecified'))}; status {_compact_text(item.get('review_status', 'needs review'))}.")
    if not assumption_findings:
        assumption_findings = ["Core assumptions include baseline emissions, reduction rate, adoption rate, CAPEX, annual savings, discount rate, and model years; each requires source and sensitivity review."]

    audit_ledger = audit.get("module_artifact_ledger", []) if isinstance(audit.get("module_artifact_ledger"), list) else []
    attached = sum(1 for x in audit_ledger if isinstance(x, dict) and x.get("status") == "attached")
    audit_findings = [f"Module artifact ledger: {attached}/{len(audit_ledger) if audit_ledger else len(module_integrations())} modules attached."]
    audit_findings.append(f"Calculation trace entries: {len(calc_trace) if calc_trace else len(audit.get('calculation_trace', []) if isinstance(audit.get('calculation_trace'), list) else [])}.")
    audit_findings.append(f"Review status: {_compact_text((audit.get('review_status') or {}).get('status', 'draft') if isinstance(audit.get('review_status'), dict) else 'draft')}.")

    brief = {
        "brief_version": APP_VERSION,
        "title": f"Integrated Decision Brief: {project_name}",
        "decision_packet_id": audit.get("decision_packet_id", "SCDS-DRAFT"),
        "decision_question": decision_question,
        "recommendation_posture": posture,
        "brief_readiness": {
            "readiness_percent": (readiness.get("brief_readiness", {}) or {}).get("readiness_percent", readiness.get("workflow_readiness_percent", 0)),
            "overall_review_state": (readiness.get("brief_readiness", {}) or {}).get("overall_review_state", "needs_review"),
            "overall_status_label": (readiness.get("brief_readiness", {}) or {}).get("overall_status_label", "Needs Review"),
            "section_statuses": (readiness.get("brief_readiness", {}) or {}).get("sections", []),
            "unresolved_issues": (readiness.get("brief_readiness", {}) or {}).get("unresolved_issues", []),
            "export_gate": (readiness.get("brief_readiness", {}) or {}).get("export_gate", {}),
            "filled_modules": readiness.get("filled_modules", []),
            "missing_modules": readiness.get("missing_modules", []),
            "review_flags": readiness.get("packet_quality", {}).get("review_flags", []),
        },
        "executive_summary": f"{project_name} is currently assessed as '{results.get('status', 'Decision requires review')}'. The four-pillar weighted score is {_brief_number(weighted)}/100, risk is {_compact_text(risk.get('risk_level'))} ({_brief_number(risk_score)}/100), estimated NPV is {_money_text(finance_results.get('npv'))}, and estimated annual avoided emissions are {_brief_number(emissions.get('annual_avoided_tco2e'))} tCO2e. Recommendation posture: {posture}.",
        "problem_framing": {"summary": _first_present(framing.get("challenge") if isinstance(framing, dict) else None, framing.get("point_of_view") if isinstance(framing, dict) else None, inputs.constraints, default="Problem framing is not yet fully imported from Catalyst Canvas.")},
        "four_pillar_analysis": {"findings": [
            f"Environmental score: {_brief_number(scores.get('environmental'))}/100.",
            f"Social score: {_brief_number(scores.get('social'))}/100.",
            f"Economic score: {_brief_number(scores.get('economic'))}/100.",
            f"Governance score: {_brief_number(scores.get('governance'))}/100.",
            f"Weighted score: {_brief_number(weighted)}/100.",
        ]},
        "scenario_comparison": {"findings": scenario_findings},
        "financial_tradeoffs": {"findings": [
            f"NPV: {_money_text(finance_results.get('npv'))}.",
            f"ROI: {_brief_number(finance_results.get('roi_percent'), '%')}.",
            f"Payback: {_brief_number(finance_results.get('payback_years'), ' years')}.",
            f"Finance outputs remain decision-support estimates until Catalyst Finance assumptions and source data are reviewed.",
        ]},
        "impact_measurement": {"findings": impact_findings},
        "claim_and_narrative_risk": {"findings": claim_findings},
        "execution_and_recovery": {"findings": recovery_findings},
        "assumptions_and_uncertainties": {"findings": assumption_findings},
        "evidence_and_source_ledger": {"findings": source_findings},
        "audit_appendix_summary": {"findings": audit_findings},
        "next_review_actions": [
            "Attach or verify Catalyst Data source records for every major claim and calculation.",
            "Review Catalyst Finance assumptions and rerun sensitivity tests before relying on financial metrics.",
            "Attach Narrative Risk review before publishing or using external-facing claims.",
            "Use Workbench for deeper symbolic, graph, engineering, or domain-specific calculations where needed.",
            "Mark required expert reviews before any regulated, safety-critical, financial, legal, engineering, or assurance use.",
        ],
        "workbench_handoffs": results.get("workbench_handoffs", []),
        "warnings": [
            "Educational decision support only. Not legal, financial, investment, engineering, medical, tax, compliance, assurance, ESG/SDG certification, or professional advice.",
            "Imported artifacts and user-provided inputs are not independently verified by Decision Studio.",
        ],
    }
    scenario_comparison = generate_scenario_comparison(ScenarioComparisonRequest(inputs=req.inputs, results=results, packet=packet)).get("scenario_comparison", {})
    workbench_handoff = generate_workbench_handoff(WorkbenchHandoffRequest(inputs=req.inputs, results=results, packet=packet, readiness=(readiness.get("brief_readiness", {}) if isinstance(readiness, dict) else {}), scenarioComparison=scenario_comparison)).get("workbench_handoff", {})
    brief["scenario_comparison_matrix"] = scenario_comparison
    brief["workbench_handoff_details"] = workbench_handoff
    brief["workbench_handoffs"] = [h.get("shortcode") for h in workbench_handoff.get("recommended_handoffs", []) if h.get("shortcode")] or results.get("workbench_handoffs", [])
    md = integrated_brief_markdown(brief)
    html = integrated_brief_html(brief)
    return {"ok": True, "version": APP_VERSION, "brief": brief, "exports": {"markdown": md, "html": html, "json": brief}, "results": results, "decision_packet": packet, "audit": audit, "readiness": readiness, "scenario_comparison": scenario_comparison, "workbench_handoff": workbench_handoff}




def _numeric(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value in (None, "", [], {}):
            return default
        return float(value)
    except Exception:
        return default


def _scenario_value(item: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in item and item.get(key) not in (None, ""):
            return item.get(key)
        camel = key.split("_")[0] + "".join(part.capitalize() for part in key.split("_")[1:])
        if camel in item and item.get(camel) not in (None, ""):
            return item.get(camel)
    return default


def _packet_scenarios(packet: Dict[str, Any]) -> List[Dict[str, Any]]:
    scenarios: List[Dict[str, Any]] = []
    raw = packet.get("scenarios", {}) if isinstance(packet, dict) else {}
    if isinstance(raw, dict):
        records = raw.get("records", [])
        if isinstance(records, list):
            scenarios.extend([x for x in records if isinstance(x, dict)])
    elif isinstance(raw, list):
        scenarios.extend([x for x in raw if isinstance(x, dict)])
    imported = packet.get("scenario_analysis") if isinstance(packet, dict) else None
    if isinstance(imported, dict):
        scenarios.append(imported)
    elif isinstance(imported, list):
        scenarios.extend([x for x in imported if isinstance(x, dict)])
    return scenarios


def scenario_comparison_template() -> Dict[str, Any]:
    return {
        "comparison_version": APP_VERSION,
        "default_options": ["Baseline", "Conservative", "Expected", "Ambitious", "Stress test"],
        "metrics": ["annual_avoided_tco2e", "total_avoided_tco2e", "npv", "payback_years", "risk_score", "confidence", "governance_burden", "implementation_complexity"],
        "decision_use": "Compare scenario options before generating the integrated brief; use Workbench handoffs for deeper modeling, graphs, sensitivity analysis, engineering review, or calculator-backed validation.",
        "warnings": ["Scenario comparison is a decision-support screen, not a forecast.", "Use reviewed sources and Workbench calculations before relying on outputs."],
    }


def generate_scenario_comparison(req: ScenarioComparisonRequest) -> Dict[str, Any]:
    inputs = req.inputs
    results = req.results or analyze(inputs)
    packet = req.packet or {}
    raw_scenarios = [x for x in req.scenarios if isinstance(x, dict)] or _packet_scenarios(packet) or results.get("scenarios", [])
    normalized: List[Dict[str, Any]] = []
    has_packet_scenarios = bool(_packet_scenarios(packet))
    for idx, item in enumerate(raw_scenarios):
        label = _first_present(_scenario_value(item, "label", "name", "scenario", "demo"), default=f"Option {idx + 1}")
        annual = _numeric(_scenario_value(item, "annual_avoided_tco2e", "annual_avoided", "emissions_reduction", "avoided_emissions"), 0)
        total = _numeric(_scenario_value(item, "total_avoided_tco2e", "total_avoided"), None)
        if total is None and annual is not None:
            total = annual * inputs.modelYears
        npv_value = _numeric(_scenario_value(item, "npv", "net_present_value"), None)
        payback = _numeric(_scenario_value(item, "payback_years", "payback"), None)
        risk = _numeric(_scenario_value(item, "risk_score", "risk"), None)
        confidence = _numeric(_scenario_value(item, "confidence", "data_confidence", "confidence_score"), inputs.dataConfidence)
        complexity = _first_present(_scenario_value(item, "implementation_complexity", "complexity"), inputs.complexity, default="Medium")
        interpretation = _first_present(_scenario_value(item, "interpretation", "decision_note", "summary", "notes"), default="Scenario generated from Decision Studio assumptions or imported artifact.")
        if risk is None:
            risk = results.get("risk", {}).get("risk_score", 50)
        npv_component = 50
        if npv_value is not None:
            npv_component = clamp(50 + (npv_value / max(inputs.capex, 1)) * 35)
        emissions_component = clamp((annual or 0) / max(inputs.baselineEmissions, 1) * 100)
        payback_component = 50 if payback is None else clamp(100 - (payback / max(inputs.modelYears, 1)) * 55)
        risk_component = clamp(100 - (risk or 50))
        confidence_component = clamp(confidence or 0)
        score = clamp((emissions_component * .26) + (npv_component * .26) + (payback_component * .16) + (risk_component * .20) + (confidence_component * .12))
        normalized.append({
            "option_id": f"scenario-{idx + 1}",
            "label": label,
            "annual_avoided_tco2e": annual,
            "total_avoided_tco2e": total,
            "npv": npv_value,
            "payback_years": payback,
            "risk_score": risk,
            "confidence": confidence,
            "implementation_complexity": complexity,
            "decision_score": round(score, 2),
            "interpretation": interpretation,
            "source": "imported_packet" if has_packet_scenarios else "decision_studio_model",
        })
    ranked = sorted(normalized, key=lambda x: x.get("decision_score", 0), reverse=True)
    ranks = {item["option_id"]: rank for rank, item in enumerate(ranked, start=1)}
    baseline = normalized[0] if normalized else {}
    matrix = []
    for item in normalized:
        row = dict(item)
        row["rank"] = ranks.get(item["option_id"])
        row["delta_vs_baseline"] = {
            "annual_avoided_tco2e": round((item.get("annual_avoided_tco2e") or 0) - (baseline.get("annual_avoided_tco2e") or 0), 4),
            "npv": None if item.get("npv") is None or baseline.get("npv") is None else round(item.get("npv") - baseline.get("npv"), 2),
            "risk_score": None if item.get("risk_score") is None or baseline.get("risk_score") is None else round(item.get("risk_score") - baseline.get("risk_score"), 2),
        }
        row["tradeoff_note"] = "High-scoring option; verify assumptions and implementation limits before export." if row.get("decision_score", 0) >= 70 else "Moderate option; review tradeoffs, sources, and mitigation requirements." if row.get("decision_score", 0) >= 50 else "Weak option under current assumptions; consider redesign or stronger evidence."
        matrix.append(row)
    best = ranked[0] if ranked else {}
    comparison = {
        "comparison_version": APP_VERSION,
        "scenario_count": len(matrix),
        "recommended_option": best.get("label", "No option selected"),
        "recommended_option_id": best.get("option_id"),
        "matrix": matrix,
        "ranked_options": ranked,
        "sensitivity_flags": ["Review savings volatility and CAPEX volatility before treating scenario ranks as stable.", "Use Workbench Graph Studio or economics forecasting for deeper sensitivity curves.", "Use Catalyst Data records to replace screening-level assumptions with source-backed indicators."],
        "workbench_handoff_candidates": ["economics-forecasting-and-scenario-tool", "risk-resilience-impact-matrix", "graph-studio-parameter-sensitivity", "environmental-monitoring-qaqc-tool"],
        "warnings": scenario_comparison_template()["warnings"],
    }
    return {"ok": True, "version": APP_VERSION, "scenario_comparison": comparison, "results": results, "decision_packet": packet}


def workbench_handoff_catalog() -> List[Dict[str, Any]]:
    return [
        {"tool_id": "economics-forecasting-and-scenario-tool", "label": "Economics Forecasting and Scenario Tool", "mode": "advanced_calculators", "use_when": "NPV, ROI, payback, benefit-cost, or scenario assumptions need sensitivity review.", "shortcode": "[sc_workbench_advanced_calculators title=\"Economics Forecasting and Scenario Tool\"]"},
        {"tool_id": "risk-resilience-impact-matrix", "label": "Risk and Resilience Matrix", "mode": "risk", "use_when": "Exposure, vulnerability, stakeholder sensitivity, resilience, or mitigation tradeoffs drive the decision.", "shortcode": "[sc_workbench topic=\"risk-resilience\" title=\"Risk and Resilience Matrix\" display=\"compact\"]"},
        {"tool_id": "graph-studio-parameter-sensitivity", "label": "Graph Studio Parameter Sensitivity", "mode": "graph", "use_when": "A user needs curves, parameter sliders, or scenario visualizations.", "shortcode": "[sc_workbench_graph_studio title=\"Scenario Sensitivity Graph\"]"},
        {"tool_id": "engineering-mode-calculation-note", "label": "Engineering Mode Calculation Note", "mode": "engineering", "use_when": "The decision includes equipment, infrastructure, energy systems, buildings, safety margins, or unit-sensitive formulas.", "shortcode": "[sc_workbench_engineering_mode title=\"Engineering Review Note\"]"},
        {"tool_id": "environmental-monitoring-qaqc-tool", "label": "Environmental Monitoring QA/QC", "mode": "environmental", "use_when": "Data confidence, source quality, indicators, thresholds, or monitoring records need validation.", "shortcode": "[sc_workbench topic=\"environmental-monitoring\" title=\"Environmental QA/QC Review\" display=\"compact\"]"},
        {"tool_id": "chalkboard-symbolic-formula-review", "label": "Chalkboard Translator and Symbolic Formula Review", "mode": "symbolic", "use_when": "Formulas, equations, or assumptions should be translated into readable math and symbolic form.", "shortcode": "[sc_workbench_chalkboard title=\"Formula Review\"]"},
        {"tool_id": "advanced-domain-calculator-library", "label": "Advanced Domain Calculator Library", "mode": "advanced", "use_when": "The decision needs econometrics, psychometrics, computational science, architecture, infrastructure, pattern recognition, or astrophysics calculators.", "shortcode": "[sc_workbench_advanced_calculators title=\"Advanced Calculator Library\"]"},
    ]


def generate_workbench_handoff(req: WorkbenchHandoffRequest) -> Dict[str, Any]:
    inputs = req.inputs
    results = req.results or analyze(inputs)
    packet = req.packet or {}
    comparison = req.scenarioComparison or generate_scenario_comparison(ScenarioComparisonRequest(inputs=inputs, results=results, packet=packet)).get("scenario_comparison", {})
    readiness = req.readiness or compute_brief_readiness(packet, inputs, results).get("brief_readiness", {})
    selected: List[Dict[str, Any]] = []
    catalog = workbench_handoff_catalog()
    requested = set(req.requestedTools or [])
    def add(tool_id: str, reason: str, priority: str = "recommended", payload: Optional[Dict[str, Any]] = None):
        for item in catalog:
            if item["tool_id"] == tool_id and not any(x["tool_id"] == tool_id for x in selected):
                selected.append({**item, "reason": reason, "priority": priority, "payload": payload or {}})
    if requested:
        for tool_id in requested:
            add(tool_id, "User-requested Workbench handoff.", "requested")
    if inputs.capex > 0 or inputs.annualSavings > 0:
        add("economics-forecasting-and-scenario-tool", "Finance outputs or scenario assumptions should be stress-tested before relying on NPV, ROI, or payback.", "high", {"capex": inputs.capex, "annualSavings": inputs.annualSavings, "discountRate": inputs.discountRate, "modelYears": inputs.modelYears})
    if inputs.exposure >= 50 or inputs.vulnerability >= 50 or results.get("risk", {}).get("risk_score", 0) >= 45:
        add("risk-resilience-impact-matrix", "Risk posture is material; use Workbench to inspect exposure, vulnerability, resilience, mitigation, and cascade effects.", "high", {"exposure": inputs.exposure, "vulnerability": inputs.vulnerability, "resilience": inputs.resilience, "risk_score": results.get("risk", {}).get("risk_score")})
    if comparison.get("scenario_count", 0) >= 3:
        add("graph-studio-parameter-sensitivity", "Multiple scenarios are present; graph scenario sensitivity and key assumption curves.", "recommended", {"scenario_comparison": comparison})
    if inputs.sector in ("Real estate and buildings", "Energy and utilities", "Manufacturing", "Transportation and logistics") or "infrastructure" in (inputs.constraints or "").lower():
        add("engineering-mode-calculation-note", "Engineering-adjacent assumptions may require unit-aware review and professional boundary notes.", "review", {"sector": inputs.sector, "constraints": inputs.constraints})
    if inputs.dataConfidence < 75 or readiness.get("counts", {}).get("sources", 0) < 1:
        add("environmental-monitoring-qaqc-tool", "Evidence/source confidence needs QA/QC before reviewed export.", "high", {"dataConfidence": inputs.dataConfidence})
    if any(sym in (inputs.constraints or "") for sym in ["=", "σ", "Δ", "CO2", "tCO", "NPV", "ROI"]):
        add("chalkboard-symbolic-formula-review", "The decision includes formula-like or technical notation that should be translated and checked.", "optional", {"constraints": inputs.constraints})
    if packet.get("scenario_comparison") or packet.get("workbench_handoffs"):
        add("advanced-domain-calculator-library", "The Decision Packet already includes advanced analysis hooks; review whether a domain-specific calculator is needed.", "optional")
    if not selected:
        add("graph-studio-parameter-sensitivity", "Use Workbench for exploratory visualization if the decision needs deeper analysis.", "optional")
    handoff = {
        "handoff_version": APP_VERSION,
        "decision_packet_id": packet.get("decision_packet_id", "SCDS-DRAFT"),
        "recommended_handoffs": selected,
        "catalog": catalog,
        "payload_summary": {"projectName": inputs.projectName, "decisionQuestion": inputs.decisionQuestion, "weighted_score": results.get("scores", {}).get("weighted"), "risk_score": results.get("risk", {}).get("risk_score"), "npv": results.get("finance", {}).get("npv"), "scenario_count": comparison.get("scenario_count", 0), "readiness_percent": readiness.get("readiness_percent", 0)},
        "workflow_note": "Decision Studio decides and synthesizes; Workbench calculates, graphs, checks formulas, and supports deeper domain analysis.",
        "warnings": ["Workbench handoffs are analytical supports, not professional approval, certification, assurance, or expert signoff."],
    }
    return {"ok": True, "version": APP_VERSION, "workbench_handoff": handoff, "scenario_comparison": comparison, "results": results, "decision_packet": packet}


def export_center_template() -> Dict[str, Any]:
    return {
        "export_center_version": APP_VERSION,
        "saved_packet_fields": [
            "decision_packet_id", "project_name", "decision_question", "status", "updated_at",
            "inputs", "results", "decision_packet", "audit", "readiness", "scenario_comparison",
            "workbench_handoff", "integrated_brief"
        ],
        "exports": [
            {"id": "packet_json", "label": "Decision Packet JSON", "description": "Complete normalized packet with module sections and raw artifact snapshots where included."},
            {"id": "integrated_brief_markdown", "label": "Integrated Brief Markdown", "description": "Reviewable decision memo for editing or publication workflow."},
            {"id": "integrated_brief_html", "label": "Integrated Brief HTML", "description": "HTML version suitable for browser print or PDF save flow."},
            {"id": "audit_json", "label": "Audit & Provenance JSON", "description": "Module ledger, source ledger, assumptions, calculation trace, claim trace, and change log."},
            {"id": "readiness_json", "label": "Readiness JSON", "description": "Section readiness, review states, unresolved issues, and export gates."},
            {"id": "scenario_json", "label": "Scenario Comparison JSON", "description": "Scenario matrix, deltas, rankings, sensitivity flags, and recommended option."},
            {"id": "handoff_json", "label": "Workbench Handoff JSON", "description": "Recommended Workbench tools, reasons, priorities, shortcodes, and payload summary."},
        ],
        "warnings": [
            "Saved Decision Packets are working records, not approvals or professional signoff.",
            "Exports preserve user-provided and imported content; review sensitive information before sharing."
        ],
    }


def _safe_packet_id(project_name: str = "Decision Packet") -> str:
    cleaned = "".join(ch for ch in project_name.upper() if ch.isalnum())[:10] or "PACKET"
    return f"SCDS-{cleaned}-DRAFT"


def generate_saved_decision_packet(req: SavedDecisionPacketRequest) -> Dict[str, Any]:
    results = req.results or analyze(req.inputs)
    packet = decision_packet_template()
    packet.update(req.packet or {})
    project_name = req.title or packet.get("project", {}).get("project_name") or req.inputs.projectName or "Decision Packet"
    decision_question = packet.get("project", {}).get("decision_question") or req.inputs.decisionQuestion
    packet_id = packet.get("decision_packet_id") or _safe_packet_id(project_name)
    readiness = req.readiness or generate_brief_readiness(BriefReadinessRequest(inputs=req.inputs, results=results, packet=packet, audit=req.audit or {})).get("readiness", {})
    scenario_comparison = req.scenarioComparison or generate_scenario_comparison(ScenarioComparisonRequest(inputs=req.inputs, results=results, packet=packet)).get("scenario_comparison", {})
    workbench_handoff = req.workbenchHandoff or generate_workbench_handoff(WorkbenchHandoffRequest(inputs=req.inputs, results=results, packet=packet, readiness=readiness, scenarioComparison=scenario_comparison)).get("workbench_handoff", {})
    audit = req.audit or generate_audit_provenance(AuditProvenanceRequest(inputs=req.inputs, results=results, packet=packet, reviewStatus=req.status)).get("audit", {})
    integrated = req.integratedBrief or generate_integrated_brief(IntegratedBriefRequest(inputs=req.inputs, results=results, packet=packet, audit=audit)).get("brief", {})
    packet["decision_packet_id"] = packet_id
    packet["saved_packet"] = {"status": req.status, "storage": "client_or_wordpress", "notes": req.notes}
    saved = {
        "packet_version": APP_VERSION,
        "decision_packet_id": packet_id,
        "title": project_name,
        "project_name": project_name,
        "decision_question": decision_question,
        "status": req.status,
        "inputs": req.inputs.model_dump(),
        "results": results,
        "decision_packet": packet,
        "audit": audit,
        "readiness": readiness,
        "scenario_comparison": scenario_comparison,
        "workbench_handoff": workbench_handoff,
        "integrated_brief": integrated,
        "notes": req.notes,
        "warnings": ["Saved packet is a review artifact; it is not approval, certification, assurance, or professional advice."],
    }
    return {"ok": True, "version": APP_VERSION, "saved_packet": saved, "export_center": export_center_template()}


def generate_export_bundle(req: ExportBundleRequest) -> Dict[str, Any]:
    inputs = req.inputs
    results = req.results or analyze(inputs)
    packet = decision_packet_template()
    packet.update(req.packet or {})
    audit = req.audit or generate_audit_provenance(AuditProvenanceRequest(inputs=inputs, results=results, packet=packet)).get("audit", {})
    readiness = req.readiness or generate_brief_readiness(BriefReadinessRequest(inputs=inputs, results=results, packet=packet, audit=audit)).get("readiness", {})
    scenario_comparison = req.scenarioComparison or generate_scenario_comparison(ScenarioComparisonRequest(inputs=inputs, results=results, packet=packet)).get("scenario_comparison", {})
    workbench_handoff = req.workbenchHandoff or generate_workbench_handoff(WorkbenchHandoffRequest(inputs=inputs, results=results, packet=packet, readiness=readiness, scenarioComparison=scenario_comparison)).get("workbench_handoff", {})
    brief_payload = req.integratedBrief or generate_integrated_brief(IntegratedBriefRequest(inputs=inputs, results=results, packet=packet, audit=audit))
    brief = brief_payload.get("brief", brief_payload) if isinstance(brief_payload, dict) else {}
    markdown = integrated_brief_markdown(brief) if brief else "# Integrated Decision Brief\n\nNo brief generated."
    html = integrated_brief_html(brief) if brief else "<h1>Integrated Decision Brief</h1><p>No brief generated.</p>"
    bundle = {
        "bundle_version": APP_VERSION,
        "label": req.exportLabel,
        "decision_packet_id": packet.get("decision_packet_id", audit.get("decision_packet_id", "SCDS-DRAFT")),
        "project_name": packet.get("project", {}).get("project_name") or inputs.projectName,
        "decision_question": packet.get("project", {}).get("decision_question") or inputs.decisionQuestion,
        "exports": {
            "decision_packet_json": packet,
            "inputs_json": inputs.model_dump(),
            "results_json": results,
            "integrated_brief_json": brief,
            "integrated_brief_markdown": markdown,
            "integrated_brief_html": html,
            "audit_json": audit,
            "readiness_json": readiness,
            "scenario_comparison_json": scenario_comparison,
            "workbench_handoff_json": workbench_handoff,
        },
        "export_manifest": export_center_template()["exports"],
        "warnings": export_center_template()["warnings"],
    }
    if not req.includeRawArtifacts:
        bundle["exports"]["decision_packet_json"].pop("module_artifacts_raw", None)
    return {"ok": True, "version": APP_VERSION, "export_bundle": bundle, "export_center": export_center_template()}


def public_landing_template() -> Dict[str, Any]:
    """Professional public-facing product-page structure for Decision Studio v1.7.1."""
    return {
        "page_version": APP_VERSION,
        "headline": "Decision Studio",
        "positioning": "An integrated sustainability decision-support workspace that turns framing, evidence, scenarios, impact measures, claims, financial tradeoffs, recovery factors, and audit provenance into a reviewable four-pillar decision brief.",
        "primary_shortcode": "[sc_decision_studio mode=\"full\" title=\"Sustainable Catalyst Decision Studio\"]",
        "landing_shortcode": "[sc_decision_studio mode=\"landing\" title=\"Sustainable Catalyst Decision Studio\"]",
        "demo_shortcode": "[sc_decision_studio mode=\"demo\" title=\"Sustainable Catalyst Decision Studio Demo\"]",
        "workflow": [
            {"step": "Frame", "module": "Catalyst Canvas", "output": "Decision question, audience, POV, HMW prompt, prototype, and test plan"},
            {"step": "Anchor", "module": "Catalyst Data", "output": "Evidence records, sources, confidence, period, and method notes"},
            {"step": "Model", "module": "Catalyst Analytics R", "output": "Scenario assumptions, emissions budget, trajectories, and interpretation notes"},
            {"step": "Measure", "module": "Global Impact Catalyst", "output": "Impact records, baselines, current values, targets, and progress notes"},
            {"step": "Review", "module": "Narrative Risk", "output": "Claim review, evidence strength, uncertainty, volatility, and consequence flags"},
            {"step": "Evaluate", "module": "Catalyst Finance", "output": "NPV, ROI, payback, benefit-cost ratio, carbon cost, and tradeoff flags"},
            {"step": "Sustain", "module": "Catalyst Grit", "output": "Recovery pressure, energy, support, clarity, next actions, and execution risk"},
            {"step": "Decide", "module": "Decision Studio", "output": "Four-pillar brief, audit appendix, readiness gate, export bundle, and Workbench handoffs"},
        ],
        "sections": [
            "Integrated platform workflow",
            "Decision Packet workspace",
            "Module artifact adapters",
            "Audit and provenance",
            "Brief readiness and review status",
            "Scenario comparison",
            "Workbench handoff",
            "Saved packets and export center",
        ],
        "boundaries": [
            "Educational and decision-support oriented; not professional advice.",
            "No ESG, SDG, assurance, compliance, engineering, legal, medical, financial, tax, or investment certification.",
            "AI may assist drafting and interpretation; deterministic calculations, assumptions, and human review remain visible.",
        ],
    }


def public_demo_template() -> Dict[str, Any]:
    """Professional demo-page structure for landing pages and platform demos."""
    return {
        "demo_version": APP_VERSION,
        "headline": "Decision Studio Demo",
        "recommended_demo_flow": [
            "Open the demo with default fleet-electrification inputs.",
            "Run the scorecard and review four-pillar results.",
            "Generate brief readiness and check unresolved issues.",
            "Compare scenarios and inspect baseline deltas.",
            "Generate Workbench handoff recommendations.",
            "Save the Decision Packet locally or export a complete bundle.",
        ],
        "demo_cards": [
            {"title": "Integrated Workflow", "description": "Show how Canvas, Data, Analytics R, Global Impact, Narrative Risk, Finance, Grit, and Decision Studio fit together.", "shortcode": "[sc_decision_studio mode=\"workflow\"]"},
            {"title": "Readiness Review", "description": "Check whether the packet is complete enough for a draft brief or export.", "shortcode": "[sc_decision_studio mode=\"readiness\"]"},
            {"title": "Scenario Comparison", "description": "Rank baseline, conservative, expected, ambitious, and stress-test options.", "shortcode": "[sc_decision_studio mode=\"scenario\"]"},
            {"title": "Export Center", "description": "Generate JSON, Markdown, HTML, audit, readiness, scenario, and handoff exports.", "shortcode": "[sc_decision_studio mode=\"export\"]"},
        ],
        "public_copy": "Use Canvas to frame. Use Data to anchor. Use Analytics R to model. Use Global Impact to measure. Use Narrative Risk to review. Use Finance to evaluate. Use Grit to sustain. Use Decision Studio to decide.",
    }

def _env_first(*names: str) -> str:
    """Return the first non-empty environment variable from a list of accepted names."""
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return ""


def ai_provider_status() -> Dict[str, Any]:
    requested_provider = os.getenv("SCDS_AI_PROVIDER", "").strip().lower()
    gemini_key = bool(_env_first("SCDS_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"))
    openai_key = bool(_env_first("SCDS_OPENAI_API_KEY", "OPENAI_API_KEY"))

    if requested_provider in {"gemini", "openai", "none"}:
        provider = requested_provider
    elif gemini_key:
        provider = "gemini"
    elif openai_key:
        provider = "openai"
    else:
        provider = "none"

    model = _env_first("SCDS_AI_MODEL", "SCDS_GEMINI_MODEL", "GEMINI_MODEL", "SCDS_OPENAI_MODEL", "OPENAI_MODEL")
    if not model and provider == "gemini":
        model = "gemini-2.5-flash"
    elif not model and provider == "openai":
        model = "gpt-5.5"

    configured = (provider == "gemini" and gemini_key) or (provider == "openai" and openai_key)
    return {
        "provider": provider,
        "configured": configured,
        "model": model,
        "gemini_key_set": gemini_key,
        "openai_key_set": openai_key,
        "backend_only": True,
    }


def deterministic_brief(inputs: DecisionInputs, results: Dict[str, Any], reason: str = "deterministic_fallback") -> Dict[str, Any]:
    scores = results.get("scores", {})
    finance = results.get("finance", {})
    emissions = results.get("emissions", {})
    risk = results.get("risk", {})
    weighted = float(scores.get("weighted", 0) or 0)
    risk_score = float(risk.get("risk_score", 0) or 0)
    status = results.get("status", "Decision requires review")
    posture = "advance with defined mitigations" if weighted >= 70 and risk_score < 60 else "revise before approval" if weighted < 60 or risk_score >= 70 else "continue due diligence"
    return {
        "source": reason,
        "ai_used": False,
        "executive_summary": f"{inputs.projectName} is assessed as: {status}. The current decision posture is to {posture}. Weighted score is {weighted:.1f}/100 and risk is {risk.get('risk_level','Unknown')} ({risk_score:.1f}/100).",
        "assumption_critique": [
            "Check baseline emissions, adoption rate, cost assumptions, savings assumptions, discount rate, and time horizon before relying on the result.",
            "Clarify whether emissions reductions are gross or net of rebound effects, grid mix, maintenance changes, and lifecycle boundaries.",
            "Document data sources and confidence levels so later reviews can audit the decision logic."
        ],
        "risk_interpretation": f"The risk screen is {risk.get('risk_level','Unknown')}. Exposure, vulnerability, stakeholder sensitivity, resilience, governance readiness, and data confidence should be reviewed together rather than as isolated scores.",
        "scenario_interpretation": "The scenario table should be read as a structured sensitivity exercise, not a forecast. Compare conservative, expected, ambitious, and stress-test cases before committing resources.",
        "stakeholder_impact_summary": "Stakeholder impact requires review of affected workers, customers, communities, suppliers, public institutions, and long-term users. Benefits and burdens should be made explicit.",
        "governance_readiness": "Decision quality depends on named accountability, monitoring cadence, data ownership, procurement controls, risk escalation, and post-implementation review.",
        "recommendation_caveats": [
            "Do not treat the score as certification, assurance, legal advice, investment advice, engineering approval, or compliance approval.",
            "Use professional review for regulated, safety-critical, financial, engineering, medical, tax, legal, or assurance contexts.",
            "Keep AI-generated language subordinate to the deterministic model, assumptions log, and human review."
        ],
        "workbench_handoffs": results.get("workbench_handoffs", []),
        "metrics_snapshot": {
            "weighted_score": weighted,
            "risk_score": risk_score,
            "npv": finance.get("npv"),
            "payback_years": finance.get("payback_years"),
            "annual_avoided_tco2e": emissions.get("annual_avoided_tco2e")
        }
    }


def brief_prompt(inputs: DecisionInputs, results: Dict[str, Any], audience: str) -> str:
    payload = {"inputs": inputs.model_dump(), "results": results}
    return (
        "You are Sustainable Catalyst Decision Studio. Produce a site-scoped, cautious decision-support brief. "
        "Do not give legal, financial, investment, engineering, medical, tax, ESG/SDG assurance, compliance, or safety-critical advice. "
        "Use the deterministic scores as evidence, critique assumptions, identify risks, explain scenarios, and include caveats. "
        "Return concise JSON with keys: executive_summary, assumption_critique, risk_interpretation, scenario_interpretation, "
        "stakeholder_impact_summary, governance_readiness, recommendation_caveats, workbench_handoffs. "
        f"Audience: {audience}. Data: {json.dumps(payload, ensure_ascii=False)[:14000]}"
    )


def parse_json_or_wrap(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json\n", "", 1)
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    return {"executive_summary": cleaned[:3500]}


def call_gemini(prompt: str) -> Dict[str, Any]:
    key = _env_first("SCDS_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")
    model = _env_first("SCDS_GEMINI_MODEL", "GEMINI_MODEL", "SCDS_AI_MODEL") or "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.25,
            "maxOutputTokens": 1600,
            "responseMimeType": "application/json",
        },
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    obj = parse_json_or_wrap(text)
    obj["provider"] = "gemini"
    obj["model"] = model
    return obj


def call_openai(prompt: str) -> Dict[str, Any]:
    key = _env_first("SCDS_OPENAI_API_KEY", "OPENAI_API_KEY")
    model = _env_first("SCDS_OPENAI_MODEL", "OPENAI_MODEL", "SCDS_AI_MODEL") or "gpt-5.5"
    url = "https://api.openai.com/v1/responses"
    body = {"model": model, "input": prompt, "temperature": 0.25, "max_output_tokens": 1600}
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    text = data.get("output_text") or ""
    if not text:
        chunks = []
        for item in data.get("output", []):
            for part in item.get("content", []):
                if part.get("type") in ("output_text", "text"):
                    chunks.append(part.get("text", ""))
        text = "\n".join(chunks)
    obj = parse_json_or_wrap(text)
    obj["provider"] = "openai"
    obj["model"] = model
    return obj


def generate_brief(req: BriefRequest) -> Dict[str, Any]:
    results = req.results or analyze(req.inputs)
    status = ai_provider_status()
    fallback = deterministic_brief(req.inputs, results)
    if not req.useAI or not status["configured"]:
        fallback["ai_status"] = status
        return fallback
    prompt = brief_prompt(req.inputs, results, req.audience)
    try:
        if status["provider"] == "gemini":
            ai = call_gemini(prompt)
        elif status["provider"] == "openai":
            ai = call_openai(prompt)
        else:
            ai = fallback
        merged = fallback.copy()
        merged.update(ai)
        merged["source"] = "ai_backend"
        merged["ai_used"] = True
        merged["ai_status"] = status
        return merged
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, Exception) as exc:
        fallback["source"] = "deterministic_fallback_after_ai_error"
        fallback["ai_error"] = str(exc)[:500]
        fallback["ai_status"] = status
        return fallback

@app.get("/health")
def health():
    return {
        "ok": True,
        "ready": True,
        "cold_start_ready": True,
        "version": APP_VERSION,
        "service": "sustainable-catalyst-decision-studio",
        "build_fingerprint": BUILD_FINGERPRINT,
        "source_commit": SOURCE_COMMIT,
        "uptime_seconds": round(time.monotonic() - STARTED_AT_MONOTONIC, 3),
        "limits": {"max_request_bytes": MAX_REQUEST_BYTES, "public_rate_limit": PUBLIC_RATE_LIMIT, "rate_window_seconds": RATE_WINDOW_SECONDS},
        "release": release_manifest(),
    }


@app.get("/release")
def release_endpoint():
    return {"ok": True, "version": APP_VERSION, "release": release_manifest()}

@app.get("/ai/status")
def ai_status():
    return {"ok": True, "version": APP_VERSION, **ai_provider_status()}

@app.post("/analyze")
def analyze_endpoint(inputs: DecisionInputs):
    return {"ok": True, "version": APP_VERSION, "results": analyze(inputs)}

@app.post("/brief")
def brief_endpoint(req: BriefRequest):
    return {"ok": True, "version": APP_VERSION, "brief": generate_brief(req), "results": req.results or analyze(req.inputs)}

@app.post("/report")
def report_endpoint(req: ReportRequest):
    results = analyze(req.inputs)
    brief = generate_brief(BriefRequest(inputs=req.inputs, results=results, useAI=req.includeAI))
    return {"ok": True, "version": APP_VERSION, "inputs": req.inputs.model_dump(), "results": results, "brief": brief, "warnings": ["Educational decision support only. Not professional advice or certification."]}


@app.post("/integrated-brief")
def integrated_brief_endpoint(req: IntegratedBriefRequest):
    return generate_integrated_brief(req)

@app.post("/decision-packet/brief")
def decision_packet_brief_endpoint(req: IntegratedBriefRequest):
    return generate_integrated_brief(req)


@app.get("/integrations/modules")
def integrations_modules_endpoint():
    return {"ok": True, "version": APP_VERSION, "modules": module_integrations(), "workflow": [m["phase"] for m in module_integrations()]}

@app.get("/integrations/adapters")
def integrations_adapters_endpoint():
    return {"ok": True, "version": APP_VERSION, "adapters": artifact_adapter_catalog()}

@app.post("/integrations/import")
def integrations_import_endpoint(req: ArtifactImportRequest):
    return import_artifact_into_packet(req.artifact, module_id=req.moduleId, packet=req.packet, preserve_raw=req.preserveRaw)

@app.post("/decision-packet/import")
def decision_packet_import_endpoint(req: ArtifactImportRequest):
    return import_artifact_into_packet(req.artifact, module_id=req.moduleId, packet=req.packet, preserve_raw=req.preserveRaw)

@app.get("/decision-packet/template")
def decision_packet_template_endpoint():
    return {"ok": True, "version": APP_VERSION, "decision_packet": decision_packet_template(), "modules": module_integrations()}

@app.post("/decision-packet/analyze")
def decision_packet_analyze_endpoint(req: DecisionPacketRequest):
    packet = decision_packet_template()
    packet.update(req.packet or {})
    for key, artifact in (req.moduleArtifacts or {}).items():
        if isinstance(artifact, dict):
            packet = import_artifact_into_packet(artifact, module_id=key, packet=packet).get("decision_packet", packet)
        else:
            packet[key] = artifact
    return synthesize_decision_packet(packet, req.inputs)

@app.get("/review/status-template")
def review_status_template_endpoint():
    return {"ok": True, "version": APP_VERSION, "review_status_catalog": review_status_catalog(), "sections": readiness_sections()}

@app.post("/brief-readiness")
def brief_readiness_endpoint(req: BriefReadinessRequest):
    return generate_brief_readiness(req)

@app.post("/decision-packet/readiness")
def decision_packet_readiness_endpoint(req: BriefReadinessRequest):
    return generate_brief_readiness(req)

@app.post("/review/status")
def review_status_endpoint(req: BriefReadinessRequest):
    return generate_brief_readiness(req)

@app.get("/audit/template")
def audit_template_endpoint():
    return {"ok": True, "version": APP_VERSION, "audit": audit_provenance_template()}

@app.post("/audit/generate")
def audit_generate_endpoint(req: AuditProvenanceRequest):
    return generate_audit_provenance(req)

@app.get("/scenario-comparison/template")
def scenario_comparison_template_endpoint():
    return {"ok": True, "version": APP_VERSION, "template": scenario_comparison_template()}

@app.post("/scenario-comparison")
def scenario_comparison_endpoint(req: ScenarioComparisonRequest):
    return generate_scenario_comparison(req)

@app.post("/decision-packet/scenario-comparison")
def decision_packet_scenario_comparison_endpoint(req: ScenarioComparisonRequest):
    return generate_scenario_comparison(req)

@app.get("/workbench/handoffs")
def workbench_handoffs_endpoint():
    return {"ok": True, "version": APP_VERSION, "catalog": workbench_handoff_catalog()}

@app.post("/workbench/handoff")
def workbench_handoff_endpoint(req: WorkbenchHandoffRequest):
    return generate_workbench_handoff(req)

@app.post("/decision-packet/workbench-handoff")
def decision_packet_workbench_handoff_endpoint(req: WorkbenchHandoffRequest):
    return generate_workbench_handoff(req)

@app.get("/decision-packet/storage-template")
def decision_packet_storage_template_endpoint():
    return {"ok": True, "version": APP_VERSION, "storage_template": export_center_template(), "decision_packet": decision_packet_template()}

@app.post("/decision-packet/save-template")
def decision_packet_save_template_endpoint(req: SavedDecisionPacketRequest):
    return generate_saved_decision_packet(req)

@app.get("/export-center/template")
def export_center_template_endpoint():
    return {"ok": True, "version": APP_VERSION, "export_center": export_center_template()}

@app.post("/export-center/bundle")
def export_center_bundle_endpoint(req: ExportBundleRequest):
    return generate_export_bundle(req)

@app.post("/decision-packet/export-bundle")
def decision_packet_export_bundle_endpoint(req: ExportBundleRequest):
    return generate_export_bundle(req)


@app.get("/public/landing-template")
def public_landing_template_endpoint():
    return {"ok": True, "version": APP_VERSION, "landing": public_landing_template()}

@app.get("/public/demo-template")
def public_demo_template_endpoint():
    return {"ok": True, "version": APP_VERSION, "demo": public_demo_template()}


@app.get("/templates")
def templates():
    return {"scenario_templates": ["Baseline", "Conservative", "Expected", "Ambitious", "Stress test"], "shortcodes": ["[sc_decision_studio mode=\"full\"]", "[sc_decision_studio mode=\"risk\"]", "[sc_decision_studio mode=\"report\"]"], "ai_endpoints": ["/release", "/ai/status", "/brief", "/report", "/integrated-brief", "/decision-packet/brief", "/brief-readiness", "/decision-packet/readiness", "/review/status", "/scenario-comparison", "/decision-packet/scenario-comparison", "/workbench/handoff", "/decision-packet/workbench-handoff", "/decision-packet/storage-template", "/decision-packet/save-template", "/export-center/template", "/export-center/bundle", "/decision-packet/export-bundle", "/public/landing-template", "/public/demo-template"], "integration_endpoints": ["/release", "/integrations/modules", "/decision-packet/template", "/decision-packet/analyze", "/audit/template", "/audit/generate", "/review/status-template", "/brief-readiness", "/decision-packet/readiness", "/integrations/adapters", "/integrations/import", "/decision-packet/import", "/integrated-brief", "/decision-packet/brief", "/brief-readiness", "/decision-packet/readiness", "/review/status", "/scenario-comparison", "/decision-packet/scenario-comparison", "/workbench/handoff", "/decision-packet/workbench-handoff", "/decision-packet/storage-template", "/decision-packet/save-template", "/export-center/template", "/export-center/bundle", "/decision-packet/export-bundle", "/public/landing-template", "/public/demo-template"]}
