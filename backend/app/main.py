from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import json
import math
import os
import urllib.request
import urllib.error

APP_VERSION = "1.1.1"
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
        "packet_version": "1.1.1",
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
        "audit_version": "1.1.1",
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


def synthesize_decision_packet(packet: Dict[str, Any], inputs: Optional[DecisionInputs] = None) -> Dict[str, Any]:
    modules = module_integrations()
    filled = []
    missing = []
    for module in modules:
        key = module["artifact_key"]
        value = packet.get(key) or packet.get(module["decision_packet_section"])
        if value and value != {} and value != []:
            filled.append(module["id"])
        else:
            missing.append(module["id"])
    base_results = analyze(inputs or DecisionInputs())
    readiness = round((len(filled) / max(1, len(modules))) * 100, 1)
    return {
        "ok": True,
        "version": APP_VERSION,
        "decision_packet_version": "1.1.1",
        "workflow_readiness_percent": readiness,
        "filled_modules": filled,
        "missing_modules": missing,
        "module_count": len(modules),
        "synthesis": {
            "posture": base_results["status"],
            "weighted_score": base_results["scores"]["weighted"],
            "risk_level": base_results["risk"]["risk_level"],
            "risk_score": base_results["risk"]["risk_score"],
            "next_best_steps": [
                "Import or manually summarize Canvas framing before finalizing the decision question.",
                "Attach at least one traceable Catalyst Data record for each major claim.",
                "Use Finance, Narrative Risk, and Grit artifacts before treating the brief as decision-ready.",
            ],
        },
        "warnings": [
            "Integrated workflow support is a decision-support scaffold. It does not certify outcomes or replace professional review.",
            "v1.1.1 adds an Audit & Provenance layer. Deeper send/import adapters are planned for later versions.",
        ],
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


@app.get("/integrations/modules")
def integrations_modules_endpoint():
    return {"ok": True, "version": APP_VERSION, "modules": module_integrations(), "workflow": [m["phase"] for m in module_integrations()]}

@app.get("/decision-packet/template")
def decision_packet_template_endpoint():
    return {"ok": True, "version": APP_VERSION, "decision_packet": decision_packet_template(), "modules": module_integrations()}

@app.post("/decision-packet/analyze")
def decision_packet_analyze_endpoint(req: DecisionPacketRequest):
    packet = decision_packet_template()
    packet.update(req.packet or {})
    for key, artifact in (req.moduleArtifacts or {}).items():
        packet[key] = artifact
    return synthesize_decision_packet(packet, req.inputs)

@app.get("/audit/template")
def audit_template_endpoint():
    return {"ok": True, "version": APP_VERSION, "audit": audit_provenance_template()}

@app.post("/audit/generate")
def audit_generate_endpoint(req: AuditProvenanceRequest):
    return generate_audit_provenance(req)

@app.get("/templates")
def templates():
    return {"scenario_templates": ["Baseline", "Conservative", "Expected", "Ambitious", "Stress test"], "shortcodes": ["[sc_decision_studio mode=\"full\"]", "[sc_decision_studio mode=\"risk\"]", "[sc_decision_studio mode=\"report\"]"], "ai_endpoints": ["/ai/status", "/brief", "/report"], "integration_endpoints": ["/integrations/modules", "/decision-packet/template", "/decision-packet/analyze", "/audit/template", "/audit/generate"]}
