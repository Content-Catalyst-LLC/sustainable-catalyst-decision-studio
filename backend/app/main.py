from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import json
import math
import os
import urllib.request
import urllib.error

APP_VERSION = "1.2.0"
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


class ArtifactImportRequest(BaseModel):
    artifact: Dict[str, Any] = Field(default_factory=dict)
    moduleId: Optional[str] = None
    packet: Dict[str, Any] = Field(default_factory=dict)
    preserveRaw: bool = True
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
        "packet_version": "1.2.0",
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
        "audit_version": "1.2.0",
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
        "decision_packet_version": "1.2.0",
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

@app.get("/audit/template")
def audit_template_endpoint():
    return {"ok": True, "version": APP_VERSION, "audit": audit_provenance_template()}

@app.post("/audit/generate")
def audit_generate_endpoint(req: AuditProvenanceRequest):
    return generate_audit_provenance(req)

@app.get("/templates")
def templates():
    return {"scenario_templates": ["Baseline", "Conservative", "Expected", "Ambitious", "Stress test"], "shortcodes": ["[sc_decision_studio mode=\"full\"]", "[sc_decision_studio mode=\"risk\"]", "[sc_decision_studio mode=\"report\"]"], "ai_endpoints": ["/ai/status", "/brief", "/report"], "integration_endpoints": ["/integrations/modules", "/decision-packet/template", "/decision-packet/analyze", "/audit/template", "/audit/generate", "/integrations/adapters", "/integrations/import", "/decision-packet/import"]}
