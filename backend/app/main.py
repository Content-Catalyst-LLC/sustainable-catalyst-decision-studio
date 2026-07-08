from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import json
import math
import os
import urllib.request
import urllib.error

APP_VERSION = "1.0.2"
app = FastAPI(title="Sustainable Catalyst Decision Studio Backend", version=APP_VERSION)

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
    return {"ok": True, "version": APP_VERSION, "service": "sustainable-catalyst-decision-studio"}

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

@app.get("/templates")
def templates():
    return {"scenario_templates": ["Baseline", "Conservative", "Expected", "Ambitious", "Stress test"], "shortcodes": ["[sc_decision_studio mode=\"full\"]", "[sc_decision_studio mode=\"risk\"]", "[sc_decision_studio mode=\"report\"]"], "ai_endpoints": ["/ai/status", "/brief", "/report"]}
