from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import json
import re
import hashlib
import math
import os
import secrets
import threading
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

from app.outcome_monitoring import (
    OUTCOME_MONITORING_SCHEMA,
    REASSESSMENT_EVENT_SCHEMA,
    DECISION_REGISTRY_SCHEMA,
    OutcomeMonitoringRequest,
    outcome_monitoring_template,
    generate_outcome_monitoring,
)
from app.public_integration import (
    PUBLIC_API_SCHEMA,
    EMBED_DESCRIPTOR_SCHEMA,
    INSTITUTIONAL_ARCHIVE_SCHEMA,
    WEBHOOK_EVENT_SCHEMA,
    SDK_CONTRACT_SCHEMA,
    PLATFORM_CORE_GATEWAY_SCHEMA,
    PublicIntegrationRequest,
    integration_template,
    public_dossier,
    governance_public_allowed,
    readiness_embed,
    scenario_embed,
    institutional_archive,
    import_archive,
    sign_manifest,
    webhook_event,
    platform_core_gateway,
    sdk_contracts,
)

APP_VERSION = "1.15.0"
BUILD_FINGERPRINT = os.getenv("SCDS_BUILD_FINGERPRINT", "scds-v1.15.0-public-api-embeds-institutional-integration")
SOURCE_COMMIT = os.getenv("SCDS_SOURCE_COMMIT", "release-v1.15.0")
RELEASE_DATE = "2026-07-16"
DECISION_PACKET_SCHEMA = "scds-decision-packet/1.8"
PLATFORM_ARTIFACT_SCHEMA = "scds-platform-artifact/1.0"
EVIDENCE_RECORD_SCHEMA = "scds-evidence-record/1.0"
GOVERNANCE_SCHEMA = "scds-decision-governance/1.0"
REVIEW_EVENT_SCHEMA = "scds-review-event/1.0"
SCENARIO_STUDIO_SCHEMA = "scds-scenario-studio/1.0"
COLLABORATION_ROOM_SCHEMA = "scds-collaborative-decision-room/1.0"
COLLABORATION_EVENT_SCHEMA = "scds-collaboration-event/1.0"
DECISION_PACK_SCHEMA = "scds-institutional-decision-pack/1.0"
DECISION_PACK_APPLICATION_SCHEMA = "scds-decision-pack-application/1.0"
PUBLICATION_STUDIO_SCHEMA = "scds-decision-publication/1.0"
PUBLICATION_HANDOFF_SCHEMA = "scds-publication-handoff/1.0"
PUBLICATION_REDACTION_SCHEMA = "scds-publication-redaction/1.0"
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
    "/scenario-studio/analyze", "/scenario-studio/sensitivity", "/scenario-studio/threshold", "/decision-packet/scenario-studio",
    "/workbench/handoff", "/decision-packet/workbench-handoff",
    "/integrations/import", "/integrations/import-batch", "/decision-packet/import",
    "/decision-packet/save-template", "/export-center/bundle",
    "/decision-packet/export-bundle", "/audit/generate",
    "/governance/evaluate", "/governance/transition", "/decision-packet/governance",
    "/collaboration/room", "/collaboration/action", "/collaboration/comment",
    "/collaboration/change-request", "/collaboration/snapshot", "/collaboration/share",
    "/collaboration/contact-handoff", "/decision-packet/collaboration",
    "/decision-packs/apply", "/decision-packs/validate", "/decision-packet/domain-pack",
    "/publication-studio/generate", "/publication-studio/redact", "/publication-studio/handoff", "/decision-packet/publication",
    "/outcomes/evaluate", "/outcomes/record-observation", "/outcomes/reassess", "/outcomes/amend", "/outcomes/retire", "/decision-packet/outcomes",
    "/api/v1/public-dossier", "/api/v1/embeds/readiness", "/api/v1/embeds/scenario",
    "/api/v1/packets/export", "/api/v1/packets/import", "/api/v1/archive",
    "/api/v1/platform-core/gateway", "/api/v1/events", "/decision-packet/institutional-integration",
}

app = FastAPI(title="Sustainable Catalyst Decision Studio Backend", version=APP_VERSION)


def release_manifest() -> Dict[str, Any]:
    return {
        "release": APP_VERSION,
        "release_name": "Public API, Embeds, and Institutional Integration",
        "release_date": RELEASE_DATE,
        "build_fingerprint": BUILD_FINGERPRINT,
        "source_commit": SOURCE_COMMIT,
        "decision_packet_schema": DECISION_PACKET_SCHEMA,
        "platform_artifact_schema": PLATFORM_ARTIFACT_SCHEMA,
        "evidence_record_schema": EVIDENCE_RECORD_SCHEMA,
        "governance_schema": GOVERNANCE_SCHEMA,
        "review_event_schema": REVIEW_EVENT_SCHEMA,
        "scenario_studio_schema": SCENARIO_STUDIO_SCHEMA,
        "collaboration_room_schema": COLLABORATION_ROOM_SCHEMA,
        "collaboration_event_schema": COLLABORATION_EVENT_SCHEMA,
        "decision_pack_schema": DECISION_PACK_SCHEMA,
        "decision_pack_application_schema": DECISION_PACK_APPLICATION_SCHEMA,
        "publication_studio_schema": PUBLICATION_STUDIO_SCHEMA,
        "publication_handoff_schema": PUBLICATION_HANDOFF_SCHEMA,
        "publication_redaction_schema": PUBLICATION_REDACTION_SCHEMA,
        "outcome_monitoring_schema": OUTCOME_MONITORING_SCHEMA,
        "reassessment_event_schema": REASSESSMENT_EVENT_SCHEMA,
        "decision_registry_schema": DECISION_REGISTRY_SCHEMA,
        "public_api_schema": PUBLIC_API_SCHEMA,
        "embed_descriptor_schema": EMBED_DESCRIPTOR_SCHEMA,
        "institutional_archive_schema": INSTITUTIONAL_ARCHIVE_SCHEMA,
        "webhook_event_schema": WEBHOOK_EVENT_SCHEMA,
        "sdk_contract_schema": SDK_CONTRACT_SCHEMA,
        "platform_core_gateway_schema": PLATFORM_CORE_GATEWAY_SCHEMA,
        "compatibility": {
            "wordpress_plugin": APP_VERSION,
            "backend": APP_VERSION,
            "api_namespace": "scds/v1",
            "shortcodes_preserved": True,
            "packet_schema_breaking_changes": False,
            "typed_platform_artifacts": True,
            "legacy_artifact_adapters_preserved": True,
            "governance_center": True,
            "immutable_review_history": True,
            "advanced_scenario_studio": True,
            "one_way_sensitivity": True,
            "multi_variable_sensitivity": True,
            "threshold_break_even_analysis": True,
            "collaborative_decision_rooms": True,
            "wordpress_canonical_room_persistence": True,
            "private_room_sharing": True,
            "locked_approved_versions": True,
            "institutional_domain_decision_packs": True,
            "domain_pack_validation": True,
            "regulated_assurance_prohibited": True,
            "decision_briefing_publication_studio": True,
            "harvard_citation_registry": True,
            "section_visibility_and_redaction": True,
            "publication_handoffs": True,
            "governed_publication_exports": True,
            "outcomes_monitoring_reassessment": True,
            "implementation_milestones": True,
            "site_intelligence_monitoring_links": True,
            "assumption_invalidation": True,
            "reassessment_triggers": True,
            "decision_registry": True,
            "public_api_embeds_institutional_integration": True,
            "scoped_api_keys": True,
            "public_safe_dossiers": True,
            "embeddable_readiness_and_scenarios": True,
            "signed_export_manifests": True,
            "bulk_packet_exchange": True,
            "institutional_archives": True,
            "platform_core_gateway": True,
            "internal_event_records": True,
            "stable_cross_product_sdk_contract": True,
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


class TypedArtifactValidationRequest(BaseModel):
    artifact: Dict[str, Any] = Field(default_factory=dict)
    sourceProduct: Optional[str] = None
    strict: bool = False


class ArtifactBatchImportRequest(BaseModel):
    artifacts: List[Dict[str, Any]] = Field(default_factory=list, max_length=100)
    packet: Dict[str, Any] = Field(default_factory=dict)
    preserveRaw: bool = True
    strict: bool = False


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


class ScenarioStudioRequest(BaseModel):
    inputs: DecisionInputs = Field(default_factory=DecisionInputs)
    packet: Dict[str, Any] = Field(default_factory=dict)
    alternatives: List[Dict[str, Any]] = Field(default_factory=list, max_length=100)
    criteria: List[Dict[str, Any]] = Field(default_factory=list, max_length=50)
    parameterRanges: Dict[str, Any] = Field(default_factory=dict)
    sensitivityParameters: List[str] = Field(default_factory=list, max_length=20)
    thresholdTarget: Dict[str, Any] = Field(default_factory=dict)
    timeHorizons: List[int] = Field(default_factory=list, max_length=20)
    gridPoints: int = Field(5, ge=3, le=21)
    includeMultiVariable: bool = True
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
    scenarioStudio: Optional[Dict[str, Any]] = None
    workbenchHandoff: Optional[Dict[str, Any]] = None
    integratedBrief: Optional[Dict[str, Any]] = None
    collaboration: Optional[Dict[str, Any]] = None
    decisionPack: Optional[Dict[str, Any]] = None
    publicationStudio: Optional[Dict[str, Any]] = None
    outcomeMonitoring: Optional[Dict[str, Any]] = None
    institutionalIntegration: Optional[Dict[str, Any]] = None
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
    scenarioStudio: Optional[Dict[str, Any]] = None
    workbenchHandoff: Optional[Dict[str, Any]] = None
    integratedBrief: Optional[Dict[str, Any]] = None
    governance: Optional[Dict[str, Any]] = None
    collaboration: Optional[Dict[str, Any]] = None
    decisionPack: Optional[Dict[str, Any]] = None
    publicationStudio: Optional[Dict[str, Any]] = None
    outcomeMonitoring: Optional[Dict[str, Any]] = None
    institutionalIntegration: Optional[Dict[str, Any]] = None
    exportAudience: str = "internal"
    includeRawArtifacts: bool = True
    exportLabel: str = "Decision Studio Export Bundle"


class GovernanceRequest(BaseModel):
    packet: Dict[str, Any] = Field(default_factory=dict)
    currentState: str = "draft"
    requestedState: Optional[str] = None
    actor: str = ""
    actorRole: str = ""
    reason: str = ""
    decisionOwner: Dict[str, Any] = Field(default_factory=dict)
    reviewers: List[Dict[str, Any]] = Field(default_factory=list, max_length=100)
    approvalConditions: List[Dict[str, Any]] = Field(default_factory=list, max_length=100)
    exceptions: List[Dict[str, Any]] = Field(default_factory=list, max_length=100)
    conflictDeclarations: List[Dict[str, Any]] = Field(default_factory=list, max_length=100)
    signoffs: List[Dict[str, Any]] = Field(default_factory=list, max_length=100)
    reviewHistory: List[Dict[str, Any]] = Field(default_factory=list, max_length=1000)
    approvalExpiresAt: str = ""
    reassessmentDueAt: str = ""
    forceTransition: bool = False


class CollaborativeRoomRequest(BaseModel):
    packet: Dict[str, Any] = Field(default_factory=dict)
    room: Dict[str, Any] = Field(default_factory=dict)
    action: str = "evaluate"
    actor: str = ""
    actorRole: str = "observer"
    targetType: str = "decision_packet"
    targetId: str = ""
    payload: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class DecisionPackRequest(BaseModel):
    packet: Dict[str, Any] = Field(default_factory=dict)
    packId: str = "climate-energy-strategy"
    organizationProfile: Dict[str, Any] = Field(default_factory=dict)
    intakeResponses: Dict[str, Any] = Field(default_factory=dict)
    selectedCriteria: List[str] = Field(default_factory=list, max_length=100)
    selectedEvidence: List[str] = Field(default_factory=list, max_length=100)
    selectedIndicators: List[str] = Field(default_factory=list, max_length=100)
    selectedWorkbenchModels: List[str] = Field(default_factory=list, max_length=100)
    reviewerAssignments: List[Dict[str, Any]] = Field(default_factory=list, max_length=100)
    actor: str = ""
    notes: str = ""
    strict: bool = False


class PublicationStudioRequest(BaseModel):
    inputs: DecisionInputs = Field(default_factory=DecisionInputs)
    results: Optional[Dict[str, Any]] = None
    packet: Dict[str, Any] = Field(default_factory=dict)
    integratedBrief: Optional[Dict[str, Any]] = None
    governance: Optional[Dict[str, Any]] = None
    publicationType: str = "executive_decision_memo"
    audience: str = "internal"
    title: str = ""
    subtitle: str = ""
    preparedBy: str = ""
    sectionVisibility: Dict[str, str] = Field(default_factory=dict)
    redactionRules: List[Dict[str, Any]] = Field(default_factory=list, max_length=100)
    publicationTargets: List[str] = Field(default_factory=list, max_length=10)
    citationStyle: str = "Harvard"
    includeDissentingView: bool = True
    includeMonitoringPlan: bool = True
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
    """Current Sustainable Catalyst platform workflow for typed evidence handoffs."""
    return [
        {
            "id": "knowledge-library", "step": 1, "phase": "Source", "name": "Knowledge Library",
            "label": "Sources and citations", "url": "/knowledge-library/", "artifact_key": "knowledge_library_evidence",
            "decision_packet_section": "evidence_registry",
            "summary": "Import durable source records, quotations, Harvard-style citations, bibliographies, collections, and evidence notes.",
            "use_in_brief": "Sources, quotations, citations, bibliography entries, collection context, and evidence notes.",
        },
        {
            "id": "research-librarian", "step": 2, "phase": "Research", "name": "Research Librarian",
            "label": "Research routes and gaps", "url": "/research-librarian/", "artifact_key": "research_guidance",
            "decision_packet_section": "research_routes",
            "summary": "Import research routes, recommended sources, evidence gaps, related titles, and follow-up questions.",
            "use_in_brief": "Research path, source recommendations, unanswered questions, and explicit evidence gaps.",
        },
        {
            "id": "site-intelligence", "step": 3, "phase": "Observe", "name": "Site Intelligence",
            "label": "Indicators and observations", "url": "/platform/site-intelligence/", "artifact_key": "site_intelligence_evidence",
            "decision_packet_section": "live_evidence",
            "summary": "Import indicators, country dossiers, live observations, methodology records, source health, and freshness context.",
            "use_in_brief": "Indicators, observations, geographic context, source health, freshness, and methodology.",
        },
        {
            "id": "workbench", "step": 4, "phase": "Model", "name": "Workbench",
            "label": "Calculations and models", "url": "/platform/workbench/", "artifact_key": "workbench_calculations",
            "decision_packet_section": "calculation_trace",
            "summary": "Import formulas, calculations, graphs, models, code outputs, validation checks, assumptions, and technical reports.",
            "use_in_brief": "Calculated outputs, formulas, graphs, assumptions, validation checks, warnings, and technical interpretation.",
        },
        {
            "id": "research-lab", "step": 5, "phase": "Validate", "name": "Research Lab",
            "label": "Experiments and scientific artifacts", "url": "/lab/", "artifact_key": "research_lab_artifacts",
            "decision_packet_section": "experimental_evidence",
            "summary": "Import experiments, notebooks, datasets, instrument context, validation results, provenance, and scientific reports.",
            "use_in_brief": "Experimental methods, datasets, results, validation status, limitations, and scientific provenance.",
        },
        {
            "id": "platform-core", "step": 6, "phase": "Trace", "name": "Platform Core",
            "label": "Entities and evidence ledger", "url": "/platform/", "artifact_key": "platform_core_records",
            "decision_packet_section": "platform_registry",
            "summary": "Import canonical entities, Evidence Ledger records, provenance links, identifiers, signatures, and shared exchange metadata.",
            "use_in_brief": "Canonical entity identity, evidence-ledger links, provenance, integrity, and cross-product relationships.",
        },
        {
            "id": "decision-studio", "step": 7, "phase": "Decide", "name": "Decision Studio",
            "label": "Decision synthesis", "url": "/platform/decision-studio/", "artifact_key": "synthesis",
            "decision_packet_section": "integrated_decision_brief",
            "summary": "Synthesize typed evidence into scenarios, readiness findings, governance notes, an auditable brief, and export bundle.",
            "use_in_brief": "Integrated synthesis, recommendation posture, alternatives, assumptions, risks, caveats, and audit trail.",
        },
    ]


def legacy_module_integrations() -> List[Dict[str, Any]]:
    """v1.0-v1.7 workflow retained as an import-compatibility layer."""
    return [
        {"id": "catalyst-canvas", "name": "Catalyst Canvas", "artifact_key": "framing"},
        {"id": "catalyst-data", "name": "Catalyst Data", "artifact_key": "evidence_records"},
        {"id": "catalyst-analytics-r", "name": "Catalyst Analytics R", "artifact_key": "scenario_analysis"},
        {"id": "global-impact-catalyst", "name": "Global Impact Catalyst", "artifact_key": "impact_records"},
        {"id": "catalyst-narrative-risk", "name": "Narrative Risk", "artifact_key": "claim_reviews"},
        {"id": "catalyst-finance", "name": "Catalyst Finance", "artifact_key": "finance_analysis"},
        {"id": "catalyst-grit", "name": "Catalyst Grit", "artifact_key": "execution_recovery"},
    ]


def platform_handoff_contracts() -> List[Dict[str, Any]]:
    base_metadata = ["artifact_schema", "artifact_id", "artifact_type", "source", "provenance", "payload"]
    return [
        {
            "product_id": "knowledge-library", "product_name": "Knowledge Library",
            "artifact_types": ["source_record", "quotation_evidence", "citation_bundle", "bibliography", "collection_context"],
            "packet_targets": ["evidence_registry", "sources", "citations", "quotations"],
            "expected_payload": ["title", "source_type", "citation", "url", "authors", "published_at", "quotes", "evidence_notes"],
            "required_envelope": base_metadata,
        },
        {
            "product_id": "research-librarian", "product_name": "Research Librarian",
            "artifact_types": ["research_route", "source_recommendations", "evidence_gap_report", "related_titles"],
            "packet_targets": ["research_routes", "sources", "evidence_gaps", "follow_up_questions"],
            "expected_payload": ["query", "route", "recommended_sources", "evidence_gaps", "follow_up_questions", "related_titles"],
            "required_envelope": base_metadata,
        },
        {
            "product_id": "site-intelligence", "product_name": "Site Intelligence",
            "artifact_types": ["indicator_record", "country_dossier", "live_observation", "methodology_record", "source_health"],
            "packet_targets": ["live_evidence", "evidence_registry", "sources", "methodologies"],
            "expected_payload": ["indicator", "geography", "period", "value", "unit", "source", "methodology", "freshness", "confidence"],
            "required_envelope": base_metadata,
        },
        {
            "product_id": "workbench", "product_name": "Workbench",
            "artifact_types": ["calculation", "model_output", "graph", "code_result", "technical_report"],
            "packet_targets": ["calculation_trace", "workbench_calculations", "assumptions", "technical_artifacts"],
            "expected_payload": ["title", "formula", "inputs", "results", "assumptions", "validation_checks", "warnings", "report"],
            "required_envelope": base_metadata,
        },
        {
            "product_id": "research-lab", "product_name": "Research Lab",
            "artifact_types": ["experiment", "notebook", "dataset", "instrument_run", "validation_result", "scientific_report"],
            "packet_targets": ["experimental_evidence", "datasets", "evidence_registry", "calculation_trace"],
            "expected_payload": ["title", "hypothesis", "method", "dataset", "results", "validation", "limitations", "instruments"],
            "required_envelope": base_metadata,
        },
        {
            "product_id": "platform-core", "product_name": "Platform Core",
            "artifact_types": ["entity_record", "evidence_ledger_record", "provenance_link", "signed_manifest", "relationship_bundle"],
            "packet_targets": ["platform_registry", "entities", "evidence_ledger", "provenance_links"],
            "expected_payload": ["entity", "identifiers", "evidence_records", "relationships", "provenance", "signatures"],
            "required_envelope": base_metadata,
        },
    ]


def platform_contract(product_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not product_id:
        return None
    normalized = product_id.strip().lower().replace("_", "-")
    aliases = {
        "library": "knowledge-library", "knowledge": "knowledge-library",
        "librarian": "research-librarian", "research-guidance": "research-librarian",
        "site": "site-intelligence", "intelligence": "site-intelligence",
        "lab": "research-lab", "core": "platform-core", "platform": "platform-core",
    }
    normalized = aliases.get(normalized, normalized)
    return next((c for c in platform_handoff_contracts() if c["product_id"] == normalized), None)

def institutional_decision_pack_catalog() -> List[Dict[str, Any]]:
    """Reusable institutional methodologies with explicit human-review boundaries."""
    shared_boundaries = [
        "Decision-support methodology only; not legal, engineering, financial, medical, tax, compliance, or assurance certification.",
        "Qualified human review is required for regulated, safety-critical, fiduciary, clinical, or public-authority decisions.",
        "AI may organize evidence and draft questions, but cannot approve, certify, assure, or sign off a decision.",
    ]
    definitions = [
        (
            "climate-energy-strategy", "Climate and Energy Strategy", "climate_energy",
            "Evaluate decarbonization, energy transition, resilience, affordability, and implementation pathways.",
            ["decision_question", "geography", "time_horizon", "baseline_year", "emissions_boundary", "energy_system_scope"],
            [("emissions_reduction", "Emissions reduction potential", 22), ("system_reliability", "Energy-system reliability", 16), ("lifecycle_cost", "Lifecycle cost and affordability", 18), ("implementation_feasibility", "Implementation feasibility", 14), ("equity_just_transition", "Equity and just-transition effects", 16), ("climate_resilience", "Climate resilience", 14)],
            ["emissions_inventory", "energy_consumption_baseline", "technology_performance", "cost_and_financing", "grid_or_fuel_context", "stakeholder_distribution"],
            ["scope_1_2_3_emissions", "energy_intensity", "renewable_share", "levelized_cost", "reliability", "energy_burden"],
            ["energy-systems-model", "emissions-pathway-model", "lifecycle-cost-model", "risk-resilience-impact-matrix"],
            ["decision_owner", "energy_subject_matter_reviewer", "finance_reviewer", "community_or_equity_reviewer", "governance_reviewer"],
            ["Are lifecycle and rebound effects included?", "What assumptions depend on future grid or fuel conditions?", "Who bears transition costs and who receives benefits?"],
            ["baseline_boundary_documented", "alternatives_include_no_action", "uncertainty_ranges_present", "stakeholder_distribution_reviewed"],
            ["climate_strategy_memo", "energy_transition_options_analysis", "public_decarbonization_dossier"],
        ),
        (
            "infrastructure-capital-investment", "Infrastructure and Capital Investment", "infrastructure_capital",
            "Compare capital programs using lifecycle performance, resilience, public value, delivery risk, and maintainability.",
            ["decision_question", "asset_or_program", "service_area", "design_life", "capital_envelope", "delivery_constraints"],
            [("service_performance", "Service performance", 18), ("whole_life_cost", "Whole-life cost", 18), ("resilience_safety", "Resilience and safety", 20), ("delivery_feasibility", "Delivery feasibility", 14), ("environmental_impact", "Environmental impact", 14), ("public_equity", "Public access and equity", 16)],
            ["asset_condition", "demand_forecast", "capital_and_operating_costs", "hazard_exposure", "delivery_schedule", "community_impacts"],
            ["service_reliability", "condition_index", "lifecycle_cost", "schedule_risk", "hazard_downtime", "access_distribution"],
            ["infrastructure-lifecycle-model", "capital-scenario-model", "reliability-model", "risk-resilience-impact-matrix"],
            ["decision_owner", "engineering_reviewer", "finance_reviewer", "operations_reviewer", "public_interest_reviewer"],
            ["Are design standards and external safety reviews complete?", "How does deferred maintenance alter the comparison?", "What failure modes create disproportionate public harm?"],
            ["asset_baseline_documented", "whole_life_cost_present", "failure_modes_reviewed", "qualified_engineering_review_required"],
            ["capital_investment_memo", "infrastructure_options_analysis", "public_value_case"],
        ),
        (
            "urban-resilience", "Urban Resilience", "urban_resilience",
            "Assess urban interventions across hazards, infrastructure interdependencies, vulnerable populations, and recovery capacity.",
            ["decision_question", "place", "hazards", "population_scope", "infrastructure_scope", "planning_horizon"],
            [("risk_reduction", "Risk reduction", 22), ("critical_services", "Critical-service continuity", 18), ("vulnerable_populations", "Protection of vulnerable populations", 18), ("adaptability", "Adaptability under changing conditions", 14), ("implementation_capacity", "Institutional implementation capacity", 14), ("co_benefits", "Environmental and social co-benefits", 14)],
            ["hazard_profile", "exposure_and_vulnerability", "critical_infrastructure", "social_vulnerability", "response_capacity", "land_use_and_environment"],
            ["hazard_exposure", "service_downtime", "social_vulnerability", "heat_or_flood_risk", "recovery_time", "adaptive_capacity"],
            ["urban-resilience-model", "spatial-risk-screen", "critical-infrastructure-dependency-model", "scenario-stress-test"],
            ["decision_owner", "planning_reviewer", "infrastructure_reviewer", "community_reviewer", "emergency_management_reviewer"],
            ["Which populations are missing from aggregate data?", "What cascading infrastructure failures are plausible?", "Does the intervention transfer risk elsewhere?"],
            ["hazard_scenarios_present", "distributional_impacts_present", "critical_dependencies_mapped", "community_review_planned"],
            ["urban_resilience_strategy", "hazard_adaptation_options", "community_resilience_brief"],
        ),
        (
            "sustainable-procurement", "Sustainable Procurement", "procurement",
            "Compare procurement choices using total cost, supplier risk, lifecycle impact, labor and human-rights concerns, and contract governance.",
            ["decision_question", "procurement_category", "spend_or_volume", "contract_horizon", "jurisdiction", "critical_requirements"],
            [("total_cost", "Total cost of ownership", 18), ("supplier_resilience", "Supplier and continuity resilience", 16), ("environmental_lifecycle", "Environmental lifecycle performance", 16), ("labor_human_rights", "Labor and human-rights safeguards", 20), ("quality_performance", "Quality and performance", 16), ("contract_governance", "Contract transparency and governance", 14)],
            ["requirements_specification", "total_cost", "supplier_due_diligence", "lifecycle_impacts", "labor_and_human_rights", "contract_controls"],
            ["total_cost_of_ownership", "supplier_concentration", "scope_3_emissions", "due_diligence_status", "delivery_reliability", "corrective_action_closure"],
            ["total-cost-of-ownership", "supplier-risk-model", "lifecycle-comparison", "procurement-scenario-model"],
            ["decision_owner", "procurement_reviewer", "finance_reviewer", "legal_or_compliance_reviewer", "human_rights_reviewer"],
            ["Are supplier claims independently evidenced?", "What contractual controls exist for remediation?", "Could low price mask externalized labor or environmental costs?"],
            ["requirements_traceable", "supplier_evidence_reviewed", "contract_controls_defined", "qualified_legal_review_required_when_regulated"],
            ["procurement_recommendation", "supplier_options_analysis", "responsible_sourcing_record"],
        ),
        (
            "responsible-ai-governance", "Responsible AI and Technology Governance", "responsible_ai",
            "Evaluate AI or digital-system adoption across purpose, evidence, rights, safety, accountability, data governance, and operational controls.",
            ["decision_question", "system_purpose", "affected_people", "data_scope", "deployment_context", "decision_authority"],
            [("public_or_user_value", "Demonstrated user or public value", 16), ("rights_fairness", "Rights, fairness, and non-discrimination", 20), ("safety_reliability", "Safety, reliability, and robustness", 18), ("privacy_data_governance", "Privacy and data governance", 18), ("transparency_contestability", "Transparency and contestability", 14), ("accountability_operations", "Accountability and operational control", 14)],
            ["purpose_and_necessity", "data_provenance", "performance_and_failure_testing", "rights_impact", "security_and_privacy", "human_oversight_and_incident_response"],
            ["error_by_group", "override_rate", "appeal_outcome", "incident_rate", "data_quality", "monitoring_coverage"],
            ["model-performance-analysis", "fairness-error-analysis", "risk-resilience-impact-matrix", "monitoring-threshold-model"],
            ["decision_owner", "technical_reviewer", "privacy_or_security_reviewer", "rights_or_ethics_reviewer", "operations_reviewer"],
            ["Is AI necessary for the stated purpose?", "Can affected people understand and contest consequential outcomes?", "What happens when the system fails or conditions drift?"],
            ["purpose_and_necessity_documented", "affected_groups_identified", "failure_testing_present", "human_accountability_named", "qualified_legal_review_required_when_applicable"],
            ["responsible_ai_decision_memo", "technology_governance_assessment", "system_deployment_conditions"],
        ),
        (
            "research-program-approval", "Research Program Approval", "research_governance",
            "Review a proposed research program across significance, methodology, feasibility, ethics, data stewardship, and reproducibility.",
            ["decision_question", "research_question", "program_scope", "methods", "participants_or_subjects", "resource_horizon"],
            [("significance", "Scientific or public significance", 18), ("methodological_rigor", "Methodological rigor", 22), ("feasibility", "Feasibility and resources", 14), ("ethics_safeguards", "Ethics and participant safeguards", 20), ("data_reproducibility", "Data stewardship and reproducibility", 16), ("knowledge_translation", "Knowledge translation and openness", 10)],
            ["literature_basis", "protocol", "sampling_and_analysis", "ethics_and_consent", "data_management", "reproducibility_plan"],
            ["protocol_completeness", "power_or_sample_adequacy", "data_management_readiness", "reproducibility_controls", "ethics_review_status", "dissemination_plan"],
            ["experimental-design", "power-and-sample-analysis", "uncertainty-analysis", "research-validation-plan"],
            ["program_owner", "methods_reviewer", "ethics_reviewer", "data_steward", "domain_reviewer"],
            ["Does the design answer the research question?", "Are ethical and regulatory approvals outside Decision Studio identified?", "Can results be reproduced and independently interpreted?"],
            ["protocol_present", "methods_review_planned", "ethics_pathway_identified", "data_management_present", "reproducibility_plan_present"],
            ["research_program_memo", "protocol_readiness_review", "research_governance_record"],
        ),
        (
            "environmental-intervention", "Environmental Intervention", "environmental_management",
            "Compare restoration, conservation, remediation, or management interventions using ecological evidence, uncertainty, durability, and community effects.",
            ["decision_question", "ecosystem_or_site", "intervention_type", "baseline_condition", "spatial_scope", "monitoring_horizon"],
            [("ecological_effectiveness", "Ecological effectiveness", 24), ("durability", "Durability and adaptive capacity", 16), ("unintended_effects", "Avoidance of unintended effects", 16), ("community_rights", "Community rights and benefits", 16), ("feasibility_cost", "Feasibility and lifecycle cost", 14), ("monitorability", "Monitoring and learning capacity", 14)],
            ["ecological_baseline", "causal_mechanism", "alternatives_and_counterfactual", "community_and_rights", "implementation_feasibility", "monitoring_design"],
            ["habitat_condition", "species_or_biodiversity", "water_or_soil_quality", "ecosystem_service", "community_access", "intervention_durability"],
            ["environmental-monitoring-qaqc-tool", "ecological-scenario-model", "spatial-impact-analysis", "adaptive-management-thresholds"],
            ["decision_owner", "ecology_reviewer", "community_or_rights_reviewer", "monitoring_reviewer", "implementation_reviewer"],
            ["What is the counterfactual without intervention?", "Could the intervention shift ecological harm elsewhere?", "What monitoring result would trigger adaptation or termination?"],
            ["baseline_present", "causal_model_documented", "community_impacts_reviewed", "monitoring_thresholds_defined", "qualified_environmental_review_required"],
            ["environmental_intervention_memo", "restoration_options_analysis", "adaptive_management_plan"],
        ),
        (
            "humanitarian-development-program", "Humanitarian and Development Programming", "humanitarian_development",
            "Assess programs across need, protection, effectiveness, localization, feasibility, accountability, and conflict sensitivity.",
            ["decision_question", "population_and_place", "needs_and_problem", "program_horizon", "delivery_partners", "operating_constraints"],
            [("needs_relevance", "Relevance to evidenced needs", 20), ("protection_do_no_harm", "Protection and do-no-harm safeguards", 22), ("effectiveness", "Expected effectiveness", 16), ("localization_participation", "Localization and participation", 16), ("feasibility_access", "Feasibility and access", 14), ("accountability_learning", "Accountability and learning", 12)],
            ["needs_assessment", "protection_analysis", "stakeholder_participation", "conflict_and_context", "delivery_feasibility", "monitoring_accountability"],
            ["people_in_need", "coverage", "protection_incidents", "access_constraints", "local_partner_share", "feedback_resolution"],
            ["humanitarian-scenario-model", "needs-prioritization", "distributional-impact-analysis", "monitoring-threshold-model"],
            ["program_owner", "protection_reviewer", "local_partner_or_community_reviewer", "monitoring_reviewer", "security_or_access_reviewer"],
            ["Could assistance expose people to additional harm?", "Whose priorities shaped the program design?", "How will exclusion, diversion, or conflict effects be detected?"],
            ["needs_evidence_present", "protection_review_present", "participation_documented", "feedback_and_safeguarding_defined", "context_monitoring_present"],
            ["humanitarian_program_memo", "development_options_analysis", "protection_and_accountability_record"],
        ),
        (
            "organizational-policy", "Organizational Policy", "policy_governance",
            "Evaluate organizational policies across purpose, authority, evidence, feasibility, rights, implementation, and reviewability.",
            ["decision_question", "policy_problem", "authority_and_scope", "affected_groups", "implementation_owner", "review_horizon"],
            [("problem_fit", "Fit to the evidenced problem", 18), ("authority_legitimacy", "Authority and legitimacy", 16), ("rights_equity", "Rights and equity effects", 18), ("implementation_feasibility", "Implementation feasibility", 16), ("clarity_enforceability", "Clarity and enforceability", 14), ("monitoring_review", "Monitoring and reviewability", 18)],
            ["problem_definition", "authority_and_constraints", "affected_group_analysis", "alternatives", "implementation_plan", "monitoring_and_review"],
            ["policy_compliance", "service_or_process_outcome", "distributional_effect", "implementation_cost", "appeal_or_exception_rate", "review_trigger"],
            ["policy-options-matrix", "distributional-impact-analysis", "implementation-capacity-model", "monitoring-threshold-model"],
            ["policy_owner", "legal_or_authority_reviewer", "operations_reviewer", "affected_group_reviewer", "governance_reviewer"],
            ["Is the policy within the institution's authority?", "Which groups face unequal burdens or barriers?", "What evidence would justify amendment or repeal?"],
            ["authority_review_identified", "affected_groups_present", "implementation_owner_named", "exceptions_and_appeals_defined", "review_trigger_defined"],
            ["organizational_policy_memo", "policy_options_analysis", "implementation_and_review_plan"],
        ),
        (
            "advisory-diagnostic-recommendation", "Advisory Diagnostic and Recommendation", "advisory",
            "Structure evidence-based advisory diagnostics, options, recommendations, implementation conditions, and client approval records.",
            ["decision_question", "client_or_institution", "diagnostic_scope", "desired_outcomes", "constraints", "engagement_horizon"],
            [("evidence_fit", "Fit to the evidence and diagnosis", 20), ("strategic_value", "Strategic value", 18), ("implementation_feasibility", "Implementation feasibility", 18), ("risk_and_ethics", "Risk and ethical safeguards", 16), ("client_capacity", "Institutional capacity and ownership", 14), ("measurability", "Measurability and learning", 14)],
            ["diagnostic_findings", "source_and_interview_record", "constraints_and_dependencies", "options_considered", "implementation_capacity", "success_and_review_measures"],
            ["diagnostic_confidence", "stakeholder_alignment", "implementation_capacity", "risk_exposure", "milestone_completion", "outcome_signal"],
            ["strategy-options-matrix", "implementation-roadmap-model", "risk-resilience-impact-matrix", "monitoring-threshold-model"],
            ["engagement_owner", "client_decision_owner", "subject_matter_reviewer", "implementation_owner", "quality_reviewer"],
            ["Which findings are evidence versus interpretation?", "What client dependencies could invalidate the recommendation?", "What would cause the recommendation to be revised?"],
            ["diagnostic_evidence_traceable", "options_compared", "client_owner_named", "implementation_conditions_present", "approval_and_reassessment_defined"],
            ["advisory_recommendation_memo", "diagnostic_findings_report", "implementation_conditions_and_approvals"],
        ),
    ]
    packs: List[Dict[str, Any]] = []
    for item in definitions:
        pack_id, name, domain, summary, intake, criteria, evidence, indicators, models, roles, risks, readiness, briefs = item
        packs.append({
            "schema": DECISION_PACK_SCHEMA,
            "pack_version": "1.0",
            "id": pack_id,
            "name": name,
            "domain": domain,
            "summary": summary,
            "required_intake_fields": intake,
            "criteria": [{"id": cid, "label": label, "weight": weight, "type": "benefit"} for cid, label, weight in criteria],
            "required_evidence": evidence,
            "suggested_indicators": indicators,
            "workbench_models": models,
            "review_roles": roles,
            "risk_questions": risks,
            "readiness_rules": readiness,
            "brief_templates": briefs,
            "governance_defaults": {
                "approval_authority": "Named human decision owner",
                "ai_approval_allowed": False,
                "independent_review_required": True,
                "regulated_review_external": True,
            },
            "boundaries": list(shared_boundaries),
        })
    return packs


def institutional_decision_pack(pack_id: str) -> Optional[Dict[str, Any]]:
    normalized = str(pack_id or "").strip().lower().replace("_", "-")
    aliases = {
        "climate": "climate-energy-strategy", "energy": "climate-energy-strategy",
        "infrastructure": "infrastructure-capital-investment", "capital": "infrastructure-capital-investment",
        "urban": "urban-resilience", "procurement": "sustainable-procurement",
        "ai": "responsible-ai-governance", "responsible-ai": "responsible-ai-governance",
        "research": "research-program-approval", "environment": "environmental-intervention",
        "humanitarian": "humanitarian-development-program", "development": "humanitarian-development-program",
        "policy": "organizational-policy", "advisory": "advisory-diagnostic-recommendation",
    }
    normalized = aliases.get(normalized, normalized)
    return next((pack for pack in institutional_decision_pack_catalog() if pack["id"] == normalized), None)


def _pack_packet_evidence_ids(packet: Dict[str, Any]) -> set[str]:
    identifiers: set[str] = set()
    for section in ("evidence_registry", "live_evidence", "experimental_evidence", "technical_artifacts", "sources", "datasets"):
        records = packet.get(section, []) if isinstance(packet, dict) else []
        if isinstance(records, dict):
            records = records.get("records", [])
        for item in records if isinstance(records, list) else []:
            if not isinstance(item, dict):
                continue
            for key in ("requirement_id", "evidence_type", "artifact_type", "type", "id", "title", "name"):
                value = item.get(key)
                if value:
                    identifiers.add(str(value).strip().lower().replace(" ", "_"))
    return identifiers


def validate_institutional_decision_pack(req: DecisionPackRequest) -> Dict[str, Any]:
    pack = institutional_decision_pack(req.packId)
    if not pack:
        return {"ok": False, "version": APP_VERSION, "error": "unknown_decision_pack", "pack_id": req.packId}
    combined = {**(req.organizationProfile or {}), **(req.intakeResponses or {})}
    intake_status = []
    for field in pack["required_intake_fields"]:
        value = combined.get(field)
        complete = value not in (None, "", [], {})
        intake_status.append({"id": field, "complete": complete, "value_present": complete})
    selected_evidence = {str(item).strip().lower().replace(" ", "_") for item in req.selectedEvidence}
    packet_evidence = _pack_packet_evidence_ids(req.packet)
    evidence_status = []
    for evidence_id in pack["required_evidence"]:
        normalized = evidence_id.lower().replace(" ", "_")
        present = normalized in selected_evidence or normalized in packet_evidence
        evidence_status.append({"id": evidence_id, "present": present, "source": "selected" if normalized in selected_evidence else "decision_packet" if present else "missing"})
    assigned_roles = {str(item.get("role", "")).strip() for item in req.reviewerAssignments if isinstance(item, dict)}
    role_status = [{"id": role, "assigned": role in assigned_roles} for role in pack["review_roles"]]
    intake_pct = round(100 * sum(1 for item in intake_status if item["complete"]) / max(1, len(intake_status)), 1)
    evidence_pct = round(100 * sum(1 for item in evidence_status if item["present"]) / max(1, len(evidence_status)), 1)
    roles_pct = round(100 * sum(1 for item in role_status if item["assigned"]) / max(1, len(role_status)), 1)
    readiness = round(intake_pct * 0.35 + evidence_pct * 0.45 + roles_pct * 0.20, 1)
    blockers = []
    blockers += [{"code": "missing_intake", "item": item["id"], "severity": "medium", "message": f"Required intake field is missing: {item['id']}"} for item in intake_status if not item["complete"]]
    blockers += [{"code": "missing_evidence", "item": item["id"], "severity": "high", "message": f"Required evidence is missing: {item['id']}"} for item in evidence_status if not item["present"]]
    blockers += [{"code": "missing_review_role", "item": item["id"], "severity": "high" if "reviewer" in item["id"] else "medium", "message": f"Required human role is not assigned: {item['id']}"} for item in role_status if not item["assigned"]]
    return {
        "ok": True,
        "version": APP_VERSION,
        "schema": DECISION_PACK_APPLICATION_SCHEMA,
        "pack": pack,
        "validation": {
            "pack_id": pack["id"],
            "pack_name": pack["name"],
            "readiness_percent": readiness,
            "intake_completion_percent": intake_pct,
            "evidence_completion_percent": evidence_pct,
            "review_role_completion_percent": roles_pct,
            "intake_status": intake_status,
            "evidence_status": evidence_status,
            "review_role_status": role_status,
            "blockers": blockers,
            "ready_for_governance_review": not any(item["severity"] == "high" for item in blockers),
            "professional_reliance_allowed": False,
        },
    }


def apply_institutional_decision_pack(req: DecisionPackRequest) -> Dict[str, Any]:
    checked = validate_institutional_decision_pack(req)
    if not checked.get("ok"):
        return checked
    pack = checked["pack"]
    packet = decision_packet_template()
    packet.update(req.packet or {})
    selected_criteria = set(req.selectedCriteria or [item["id"] for item in pack["criteria"]])
    selected_indicators = set(req.selectedIndicators or pack["suggested_indicators"])
    selected_models = set(req.selectedWorkbenchModels or pack["workbench_models"])
    seed = {"pack_id": pack["id"], "project": packet.get("project", {}), "actor": req.actor, "responses": req.intakeResponses}
    application_id = "SCDS-PACK-" + hashlib.sha256(json.dumps(seed, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16].upper()
    application = {
        "schema": DECISION_PACK_APPLICATION_SCHEMA,
        "application_id": application_id,
        "applied_at": _utc_now(),
        "applied_by": req.actor,
        "source_product": "decision-studio",
        "source_version": APP_VERSION,
        "pack_id": pack["id"],
        "pack_name": pack["name"],
        "domain": pack["domain"],
        "pack_version": pack["pack_version"],
        "organization_profile": req.organizationProfile,
        "intake_responses": req.intakeResponses,
        "criteria": [{**item, "selected": item["id"] in selected_criteria} for item in pack["criteria"]],
        "evidence_plan": [{"id": item, "required": True, "status": next((status["source"] for status in checked["validation"]["evidence_status"] if status["id"] == item), "missing")} for item in pack["required_evidence"]],
        "indicator_plan": [{"id": item, "selected": item in selected_indicators} for item in pack["suggested_indicators"]],
        "workbench_model_plan": [{"id": item, "selected": item in selected_models, "execution_authority": "workbench"} for item in pack["workbench_models"]],
        "review_plan": {"required_roles": pack["review_roles"], "assignments": req.reviewerAssignments, "approval_authority": "named_human_decision_owner", "ai_approval_allowed": False},
        "risk_questions": pack["risk_questions"],
        "readiness_rules": pack["readiness_rules"],
        "brief_templates": pack["brief_templates"],
        "boundaries": pack["boundaries"],
        "validation": checked["validation"],
        "notes": req.notes,
    }
    packet["packet_version"] = APP_VERSION
    packet["decision_pack_schema"] = DECISION_PACK_SCHEMA
    packet["decision_pack_application_schema"] = DECISION_PACK_APPLICATION_SCHEMA
    packet["institutional_decision_pack"] = application
    packet.setdefault("decision_framing", {})["institutional_domain"] = {"pack_id": pack["id"], "pack_name": pack["name"], "domain": pack["domain"]}
    packet["criteria_registry"] = application["criteria"]
    packet["evidence_plan"] = application["evidence_plan"]
    packet["indicator_plan"] = application["indicator_plan"]
    packet["model_plan"] = application["workbench_model_plan"]
    packet.setdefault("governance_center", governance_template())["domain_pack_requirements"] = application["review_plan"]
    packet["domain_readiness_rules"] = application["readiness_rules"]
    packet["domain_brief_templates"] = application["brief_templates"]
    formats = packet.setdefault("export_center", {}).setdefault("available_formats", [])
    if "decision_pack_json" not in formats:
        formats.append("decision_pack_json")
    return {"ok": True, "version": APP_VERSION, "schema": DECISION_PACK_APPLICATION_SCHEMA, "decision_pack": application, "validation": checked["validation"], "decision_packet": packet}


def decision_packet_template() -> Dict[str, Any]:
    modules = module_integrations()
    return {
        "packet_version": "1.15.0",
        "workflow": "Knowledge Library → Research Librarian → Site Intelligence → Workbench → Research Lab → Platform Core → Decision Studio",
        "artifact_schema": PLATFORM_ARTIFACT_SCHEMA,
        "evidence_record_schema": EVIDENCE_RECORD_SCHEMA,
        "governance_schema": GOVERNANCE_SCHEMA,
        "review_event_schema": REVIEW_EVENT_SCHEMA,
        "scenario_studio_schema": SCENARIO_STUDIO_SCHEMA,
        "collaboration_room_schema": COLLABORATION_ROOM_SCHEMA,
        "collaboration_event_schema": COLLABORATION_EVENT_SCHEMA,
        "decision_pack_schema": DECISION_PACK_SCHEMA,
        "decision_pack_application_schema": DECISION_PACK_APPLICATION_SCHEMA,
        "publication_studio_schema": PUBLICATION_STUDIO_SCHEMA,
        "publication_handoff_schema": PUBLICATION_HANDOFF_SCHEMA,
        "publication_redaction_schema": PUBLICATION_REDACTION_SCHEMA,
        "outcome_monitoring_schema": OUTCOME_MONITORING_SCHEMA,
        "reassessment_event_schema": REASSESSMENT_EVENT_SCHEMA,
        "decision_registry_schema": DECISION_REGISTRY_SCHEMA,
        "public_api_schema": PUBLIC_API_SCHEMA,
        "embed_descriptor_schema": EMBED_DESCRIPTOR_SCHEMA,
        "institutional_archive_schema": INSTITUTIONAL_ARCHIVE_SCHEMA,
        "webhook_event_schema": WEBHOOK_EVENT_SCHEMA,
        "sdk_contract_schema": SDK_CONTRACT_SCHEMA,
        "platform_core_gateway_schema": PLATFORM_CORE_GATEWAY_SCHEMA,
        "project": {
            "project_name": "",
            "organization_type": "",
            "sector": "",
            "location": "",
            "time_horizon": "",
            "decision_question": "",
        },
        "decision_framing": {},
        "evidence_registry": [],
        "citations": [],
        "quotations": [],
        "research_routes": [],
        "evidence_gaps": [],
        "follow_up_questions": [],
        "live_evidence": [],
        "methodologies": [],
        "experimental_evidence": [],
        "datasets": [],
        "technical_artifacts": [],
        "platform_registry": [],
        "entities": [],
        "evidence_ledger": [],
        "provenance_links": [],
        "platform_handoffs": [],
        "integrity_checks": [],
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
        "governance_center": governance_template(),
        "collaboration_room": collaborative_room_template(),
        "institutional_decision_pack": {},
        "criteria_registry": [],
        "evidence_plan": [],
        "indicator_plan": [],
        "model_plan": [],
        "domain_readiness_rules": [],
        "domain_brief_templates": [],
        "publication_studio": {},
        "publication_registry": [],
        "publication_handoffs": [],
        "redaction_log": [],
        "outcome_monitoring": outcome_monitoring_template(),
        "decision_registry_entry": {},
        "reassessment_history": [],
        "implementation_amendments": [],
        "institutional_integration": integration_template(app_version=APP_VERSION, packet_schema=DECISION_PACKET_SCHEMA),
        "public_dossier": {},
        "embed_descriptors": [],
        "institutional_archives": [],
        "platform_core_gateway": {},
        "internal_events": [],
        "sdk_contracts": sdk_contracts(app_version=APP_VERSION, packet_schema=DECISION_PACKET_SCHEMA),
        "integrated_decision_brief": {},
        "scenario_comparison": {},
        "scenario_studio": {},
        "sensitivity_analysis": {},
        "threshold_analysis": {},
        "uncertainty_analysis": {},
        "workbench_handoffs": [],
        "saved_packet": {"saved_at": "", "saved_by": "", "status": "draft", "storage": "browser_or_wordpress"},
        "export_center": {"last_exported_at": "", "available_formats": ["json", "markdown", "html", "audit_json", "readiness_json", "scenario_json", "scenario_studio_json", "sensitivity_json", "threshold_json", "handoff_json", "governance_json", "collaboration_json", "room_activity_json", "snapshot_comparison_json", "decision_pack_json", "publication_json", "publication_markdown", "publication_html", "bibliography_json", "redaction_json", "publication_handoff_json", "outcome_monitoring_json", "decision_registry_json", "reassessment_history_json", "public_dossier_json", "readiness_embed_json", "scenario_embed_json", "institutional_archive_json", "signed_manifest_json", "platform_core_gateway_json", "internal_events_json"]},
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
        "audit_version": "1.15.0",
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
            "module_id": "knowledge-library", "name": "Knowledge Library", "artifact_key": "knowledge_library_evidence",
            "packet_section": "evidence_registry", "detects": ["citation", "bibliography", "quotes", "source_record", "evidence_notes"],
            "required_or_expected": ["title", "citation", "source_type"],
            "summary": "Normalizes source records, quotations, citations, bibliographies, collections, and evidence notes.",
        },
        {
            "module_id": "research-librarian", "name": "Research Librarian", "artifact_key": "research_guidance",
            "packet_section": "research_routes", "detects": ["research_route", "recommended_sources", "evidence_gaps", "follow_up_questions", "related_titles"],
            "required_or_expected": ["query", "route"],
            "summary": "Normalizes research routes, source recommendations, related titles, evidence gaps, and follow-up questions.",
        },
        {
            "module_id": "site-intelligence", "name": "Site Intelligence", "artifact_key": "site_intelligence_evidence",
            "packet_section": "live_evidence", "detects": ["indicator", "geography", "period", "value", "methodology", "freshness"],
            "required_or_expected": ["indicator", "value", "source"],
            "summary": "Normalizes indicators, country context, live observations, methods, source health, freshness, and confidence.",
        },
        {
            "module_id": "research-lab", "name": "Research Lab", "artifact_key": "research_lab_artifacts",
            "packet_section": "experimental_evidence", "detects": ["experiment", "hypothesis", "method", "dataset", "validation", "instruments"],
            "required_or_expected": ["title", "method", "results"],
            "summary": "Normalizes experiments, notebooks, datasets, instrument context, validation results, and limitations.",
        },
        {
            "module_id": "platform-core", "name": "Platform Core", "artifact_key": "platform_core_records",
            "packet_section": "platform_registry", "detects": ["entity", "identifiers", "evidence_ledger", "relationships", "provenance", "signatures"],
            "required_or_expected": ["entity"],
            "summary": "Normalizes canonical entities, evidence-ledger records, provenance links, relationships, and signatures.",
        },
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
        "library": "knowledge-library",
        "knowledge": "knowledge-library",
        "librarian": "research-librarian",
        "research-guidance": "research-librarian",
        "site": "site-intelligence",
        "intelligence": "site-intelligence",
        "lab": "research-lab",
        "core": "platform-core",
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
    envelope_source = artifact.get("source", {}) if isinstance(artifact.get("source"), dict) else {}
    source_product = artifact.get("source_product") or artifact.get("sourceProduct") or envelope_source.get("product") or envelope_source.get("product_id")
    if source_product and _adapter_by_id(str(source_product)):
        return _adapter_by_id(str(source_product))
    payload = artifact.get("payload") if isinstance(artifact.get("payload"), dict) else artifact
    keys = set(payload.keys())
    artifact_type = str(artifact.get("artifact_type", artifact.get("type", ""))).lower()
    if artifact_type in {"source_record", "quotation_evidence", "citation_bundle", "bibliography", "collection_context"} or {"citation", "bibliography"} & keys:
        return _adapter_by_id("knowledge-library")
    if artifact_type in {"research_route", "source_recommendations", "evidence_gap_report", "related_titles"} or {"recommended_sources", "evidence_gaps", "follow_up_questions"} & keys:
        return _adapter_by_id("research-librarian")
    if artifact_type in {"indicator_record", "country_dossier", "live_observation", "methodology_record", "source_health"} or ({"indicator", "value"}.issubset(keys) and ("geography" in keys or "freshness" in keys)):
        return _adapter_by_id("site-intelligence")
    if artifact_type in {"experiment", "notebook", "dataset", "instrument_run", "validation_result", "scientific_report"} or {"hypothesis", "method", "validation"} & keys:
        return _adapter_by_id("research-lab")
    if artifact_type in {"entity_record", "evidence_ledger_record", "provenance_link", "signed_manifest", "relationship_bundle"} or {"identifiers", "evidence_ledger", "relationships", "signatures"} & keys:
        return _adapter_by_id("platform-core")
    record_type = str(payload.get("record_type", "")).lower()
    artifact = payload
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
        if key in {"assumptions", "risks", "sources", "audit_trail", "calculation_trace", "claim_reviews", "workbench_calculations", "evidence_registry", "citations", "quotations", "research_routes", "evidence_gaps", "follow_up_questions", "live_evidence", "methodologies", "experimental_evidence", "datasets", "technical_artifacts", "platform_registry", "entities", "evidence_ledger", "provenance_links", "platform_handoffs", "integrity_checks"}:
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
    out["module_slots"] = slots
    return out


def normalize_legacy_artifact(artifact: Dict[str, Any], module_id: Optional[str] = None, preserve_raw: bool = True) -> Dict[str, Any]:
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



def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _typed_envelope(artifact: Dict[str, Any], module_id: Optional[str] = None) -> Dict[str, Any]:
    adapter = detect_artifact_adapter(artifact, module_id)
    source = artifact.get("source", {}) if isinstance(artifact.get("source"), dict) else {}
    provenance = artifact.get("provenance", {}) if isinstance(artifact.get("provenance"), dict) else {}
    payload = artifact.get("payload") if isinstance(artifact.get("payload"), dict) else artifact
    source_product = (
        module_id or artifact.get("source_product") or artifact.get("sourceProduct")
        or source.get("product") or source.get("product_id") or adapter["module_id"]
    )
    contract = platform_contract(str(source_product))
    product_id = contract["product_id"] if contract else adapter["module_id"]
    artifact_type = str(artifact.get("artifact_type") or artifact.get("type") or adapter["artifact_key"]).strip()
    supplied_hash = str(provenance.get("integrity_hash") or artifact.get("integrity_hash") or "").strip()
    calculated_hash = _canonical_hash(payload)
    return {
        "artifact_schema": str(artifact.get("artifact_schema") or PLATFORM_ARTIFACT_SCHEMA),
        "artifact_id": str(artifact.get("artifact_id") or artifact.get("id") or calculated_hash.split(":", 1)[1][:20]),
        "artifact_type": artifact_type,
        "source": {
            "product": product_id,
            "product_version": str(source.get("product_version") or source.get("version") or artifact.get("source_version") or "unknown"),
            "artifact_url": str(source.get("artifact_url") or source.get("url") or artifact.get("url") or ""),
            "created_at": str(source.get("created_at") or artifact.get("created_at") or ""),
            "exported_at": str(source.get("exported_at") or artifact.get("exported_at") or _utc_now()),
        },
        "provenance": {
            "methodology": provenance.get("methodology") or artifact.get("methodology") or payload.get("methodology", ""),
            "freshness": provenance.get("freshness") or artifact.get("freshness") or payload.get("freshness", "unspecified"),
            "confidence": provenance.get("confidence") if provenance.get("confidence") is not None else artifact.get("confidence", payload.get("confidence", "unspecified")),
            "integrity_hash": supplied_hash or calculated_hash,
            "calculated_integrity_hash": calculated_hash,
            "integrity_verified": bool(supplied_hash and supplied_hash == calculated_hash),
            "transformation_history": _list(provenance.get("transformation_history")) + [{"at": _utc_now(), "action": "normalized", "by": "decision-studio", "version": APP_VERSION}],
        },
        "payload": payload,
    }


def validate_typed_artifact(artifact: Dict[str, Any], source_product: Optional[str] = None, strict: bool = False) -> Dict[str, Any]:
    envelope = _typed_envelope(artifact, source_product)
    product_id = envelope["source"]["product"]
    contract = platform_contract(product_id)
    errors: List[str] = []
    warnings: List[str] = []
    if not contract:
        errors.append(f"Unsupported platform source product: {product_id}")
    if envelope["artifact_schema"] != PLATFORM_ARTIFACT_SCHEMA:
        message = f"Artifact schema {envelope['artifact_schema']} differs from supported {PLATFORM_ARTIFACT_SCHEMA}."
        (errors if strict else warnings).append(message)
    if not isinstance(envelope["payload"], dict) or not envelope["payload"]:
        errors.append("Artifact payload must be a non-empty object.")
    if contract and envelope["artifact_type"] not in contract["artifact_types"]:
        warnings.append(f"Artifact type {envelope['artifact_type']} is not in the registered {product_id} type catalog.")
    supplied = str((artifact.get("provenance") or {}).get("integrity_hash", "")) if isinstance(artifact.get("provenance"), dict) else str(artifact.get("integrity_hash", ""))
    if supplied and not envelope["provenance"]["integrity_verified"]:
        errors.append("Supplied integrity hash does not match the canonical payload hash.")
    return {
        "ok": not errors, "version": APP_VERSION, "schema": PLATFORM_ARTIFACT_SCHEMA,
        "product_id": product_id, "contract": contract, "envelope": envelope,
        "errors": errors, "warnings": warnings,
    }


def normalize_platform_artifact(artifact: Dict[str, Any], module_id: Optional[str] = None, preserve_raw: bool = True) -> Dict[str, Any]:
    validation = validate_typed_artifact(artifact, module_id, strict=False)
    envelope = validation["envelope"]
    product_id = envelope["source"]["product"]
    payload = envelope["payload"]
    adapter = _adapter_by_id(product_id) or detect_artifact_adapter(artifact, module_id)
    name = adapter["name"]
    evidence_base = {
        "evidence_schema": EVIDENCE_RECORD_SCHEMA,
        "artifact_id": envelope["artifact_id"],
        "artifact_type": envelope["artifact_type"],
        "source_product": product_id,
        "source_version": envelope["source"]["product_version"],
        "source_url": envelope["source"]["artifact_url"],
        "methodology": envelope["provenance"]["methodology"],
        "freshness": envelope["provenance"]["freshness"],
        "confidence": envelope["provenance"]["confidence"],
        "integrity_hash": envelope["provenance"]["calculated_integrity_hash"],
        "integrity_verified": envelope["provenance"]["integrity_verified"],
    }
    patch: Dict[str, Any] = {
        "platform_handoffs": [envelope],
        "integrity_checks": [{
            "artifact_id": envelope["artifact_id"], "source_product": product_id,
            "supplied_hash": envelope["provenance"]["integrity_hash"],
            "calculated_hash": envelope["provenance"]["calculated_integrity_hash"],
            "verified": envelope["provenance"]["integrity_verified"],
        }],
        "audit_trail": [{"event": "Typed platform artifact imported", "module": name, "module_id": product_id, "artifact_id": envelope["artifact_id"], "version": APP_VERSION}],
    }
    warnings = list(validation["warnings"])

    if product_id == "knowledge-library":
        records = _list(payload.get("sources") or payload.get("source_records") or payload.get("records"))
        if not records:
            records = [payload]
        evidence_records, sources, citations, quotations = [], [], [], []
        for item in records:
            item = item if isinstance(item, dict) else {"title": str(item)}
            title = str(item.get("title") or item.get("source_title") or payload.get("title") or "Knowledge Library source")
            record = {**evidence_base, "title": title, "source_type": item.get("source_type", payload.get("source_type", "research source")), "citation": item.get("citation", payload.get("citation", "")), "authors": item.get("authors", payload.get("authors", [])), "published_at": item.get("published_at", payload.get("published_at", "")), "evidence_notes": item.get("evidence_notes", payload.get("evidence_notes", "")), "collection": item.get("collection", payload.get("collection", ""))}
            evidence_records.append(record)
            sources.append(_source_entry(title, record["source_type"], evidence_base["confidence"], "Knowledge Library evidence", str(record["evidence_notes"])))
            if record["citation"]:
                citations.append({"artifact_id": envelope["artifact_id"], "citation": record["citation"], "style": item.get("citation_style", payload.get("citation_style", "Harvard")), "title": title})
            for quote in _list(item.get("quotes") or item.get("quotations") or payload.get("quotes") or payload.get("quotations")):
                quotations.append({"artifact_id": envelope["artifact_id"], "source_title": title, "quote": quote.get("text", "") if isinstance(quote, dict) else str(quote), "locator": quote.get("locator", "") if isinstance(quote, dict) else "", "context": quote.get("context", "") if isinstance(quote, dict) else ""})
        patch.update({"evidence_registry": evidence_records, "sources": sources, "citations": citations, "quotations": quotations, "knowledge_library_evidence": evidence_records})
        title = evidence_records[0]["title"]
    elif product_id == "research-librarian":
        route = {**evidence_base, "query": payload.get("query", ""), "route": payload.get("route") or payload.get("research_route") or [], "recommended_sources": _list(payload.get("recommended_sources")), "related_titles": _list(payload.get("related_titles")), "notes": payload.get("notes", "")}
        source_records = []
        for source in route["recommended_sources"]:
            src = source if isinstance(source, dict) else {"title": str(source)}
            source_records.append(_source_entry(str(src.get("title") or src.get("name") or "Recommended source"), str(src.get("type") or "research recommendation"), src.get("confidence", evidence_base["confidence"]), "Research Librarian recommendation", str(src.get("reason") or "")))
        patch.update({"research_routes": [route], "research_guidance": route, "sources": source_records, "evidence_gaps": _list(payload.get("evidence_gaps")), "follow_up_questions": _list(payload.get("follow_up_questions"))})
        title = str(payload.get("query") or "Research Librarian route")
    elif product_id == "site-intelligence":
        record = {**evidence_base, "indicator": payload.get("indicator", {}), "geography": payload.get("geography") or payload.get("country") or payload.get("region") or "", "period": payload.get("period") or payload.get("observed_at") or "", "value": payload.get("value"), "unit": payload.get("unit", ""), "source": payload.get("source", {}), "source_health": payload.get("source_health", {}), "observation_type": envelope["artifact_type"]}
        source = payload.get("source", {}) if isinstance(payload.get("source"), dict) else {"name": payload.get("source")}
        source_title = str(source.get("name") or source.get("title") or "Site Intelligence source")
        patch.update({"live_evidence": [record], "site_intelligence_evidence": [record], "evidence_registry": [record], "sources": [_source_entry(source_title, str(source.get("type") or "public data source"), evidence_base["confidence"], str(payload.get("indicator") or "indicator evidence"), str(evidence_base["methodology"]))], "methodologies": _list(payload.get("methodology_records") or payload.get("methodology"))})
        title = str(payload.get("indicator") or payload.get("title") or "Site Intelligence observation")
    elif product_id == "workbench":
        calc = {**evidence_base, "calculation": payload.get("calculation") or payload.get("title") or "Workbench artifact", "formula": payload.get("formula", ""), "inputs": payload.get("inputs", {}), "results": payload.get("results", payload.get("result")), "assumptions": _list(payload.get("assumptions")), "validation_checks": _list(payload.get("validation_checks") or payload.get("checks")), "warnings": _list(payload.get("warnings")), "graph": payload.get("graph", {}), "report": payload.get("report", {})}
        patch.update({"workbench_calculations": [calc], "technical_artifacts": [calc], "calculation_trace": [{"artifact_id": envelope["artifact_id"], "calculation": calc["calculation"], "formula": calc["formula"], "inputs": calc["inputs"], "result": calc["results"], "unit": payload.get("unit", ""), "validation_status": "imported from Workbench", "validation_checks": calc["validation_checks"]}], "assumptions": [_assumption(str(a.get("name") or a.get("assumption") or "Workbench assumption"), a.get("value"), name, "technical model", str(a.get("sensitivity") or "medium"), str(a.get("review_status") or "needs review")) if isinstance(a, dict) else _assumption(str(a), None, name, "technical model") for a in calc["assumptions"]]})
        title = calc["calculation"]
    elif product_id == "research-lab":
        record = {**evidence_base, "title": payload.get("title") or payload.get("experiment") or "Research Lab artifact", "hypothesis": payload.get("hypothesis", ""), "method": payload.get("method", {}), "results": payload.get("results", {}), "validation": payload.get("validation", {}), "limitations": _list(payload.get("limitations")), "instruments": _list(payload.get("instruments")), "notebook": payload.get("notebook", {})}
        datasets = _list(payload.get("datasets") or payload.get("dataset"))
        patch.update({"experimental_evidence": [record], "research_lab_artifacts": [record], "datasets": datasets, "evidence_registry": [record]})
        if payload.get("calculation_trace"):
            patch["calculation_trace"] = _list(payload.get("calculation_trace"))
        title = record["title"]
    elif product_id == "platform-core":
        entity = payload.get("entity") if isinstance(payload.get("entity"), dict) else {"name": payload.get("entity") or payload.get("name") or "Platform entity"}
        registry = {**evidence_base, "entity": entity, "identifiers": payload.get("identifiers", {}), "relationships": _list(payload.get("relationships")), "signatures": _list(payload.get("signatures"))}
        ledger = _list(payload.get("evidence_ledger") or payload.get("evidence_records"))
        links = _list(payload.get("provenance_links") or payload.get("provenance"))
        patch.update({"platform_registry": [registry], "platform_core_records": [registry], "entities": [entity], "evidence_ledger": ledger, "provenance_links": links})
        title = str(entity.get("name") or entity.get("title") or "Platform Core entity")
    else:
        return normalize_legacy_artifact(artifact, module_id=module_id, preserve_raw=preserve_raw)

    if preserve_raw:
        patch.setdefault("module_artifacts_raw", {})[adapter["artifact_key"]] = artifact
    summary = {
        "module_id": product_id, "module_name": name, "artifact_key": adapter["artifact_key"],
        "packet_section": adapter["packet_section"], "artifact_id": envelope["artifact_id"],
        "artifact_type": envelope["artifact_type"], "title": title, "status": "typed_and_normalized",
        "integrity_verified": envelope["provenance"]["integrity_verified"],
    }
    return {"ok": validation["ok"], "version": APP_VERSION, "schema": PLATFORM_ARTIFACT_SCHEMA, "adapter": adapter, "contract": validation["contract"], "summary": summary, "packet_patch": patch, "warnings": warnings, "validation": validation, "artifact": envelope}


def normalize_artifact(artifact: Dict[str, Any], module_id: Optional[str] = None, preserve_raw: bool = True) -> Dict[str, Any]:
    adapter = detect_artifact_adapter(artifact, module_id)
    if platform_contract(adapter["module_id"]):
        return normalize_platform_artifact(artifact, module_id=adapter["module_id"], preserve_raw=preserve_raw)
    return normalize_legacy_artifact(artifact, module_id=module_id, preserve_raw=preserve_raw)


def import_artifact_batch(artifacts: List[Dict[str, Any]], packet: Optional[Dict[str, Any]] = None, preserve_raw: bool = True, strict: bool = False) -> Dict[str, Any]:
    updated = packet or decision_packet_template()
    imported: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for index, artifact in enumerate(artifacts[:100]):
        if not isinstance(artifact, dict):
            rejected.append({"index": index, "errors": ["Artifact must be an object."]})
            continue
        validation = validate_typed_artifact(artifact, None, strict=strict)
        if strict and not validation["ok"]:
            rejected.append({"index": index, "artifact_id": validation["envelope"]["artifact_id"], "errors": validation["errors"], "warnings": validation["warnings"]})
            continue
        result = import_artifact_into_packet(artifact, packet=updated, preserve_raw=preserve_raw)
        updated = result["decision_packet"]
        imported.append(result["import_result"]["summary"])
    analysis = synthesize_decision_packet(updated, None)
    return {"ok": not rejected or not strict, "version": APP_VERSION, "imported_count": len(imported), "rejected_count": len(rejected), "imports": imported, "rejected": rejected, "decision_packet": updated, "analysis": analysis}

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
    legacy_filled = []
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
    legacy_map = {
        "catalyst-canvas": packet.get("decision_framing") or packet.get("framing"),
        "catalyst-data": packet.get("evidence_and_measurement") or packet.get("evidence_records"),
        "catalyst-analytics-r": packet.get("scenarios") or packet.get("scenario_analysis"),
        "global-impact-catalyst": packet.get("impact_measurement") or packet.get("impact_records"),
        "catalyst-narrative-risk": packet.get("claim_and_risk_review") or packet.get("claim_reviews"),
        "catalyst-finance": packet.get("financial_tradeoffs") or packet.get("finance_analysis"),
        "catalyst-grit": packet.get("execution_and_recovery") or packet.get("execution_recovery"),
    }
    legacy_filled = [module_id for module_id, value in legacy_map.items() if _nonempty(value)]
    workbench_attached = _nonempty(packet.get("workbench_calculations")) or _nonempty(packet.get("calculation_trace"))
    base_results = analyze(inputs or DecisionInputs())
    readiness = round((len(filled) / max(1, len(modules))) * 100, 1)
    source_count = len(packet.get("sources", [])) if isinstance(packet.get("sources", []), list) else 0
    assumption_count = len(packet.get("assumptions", [])) if isinstance(packet.get("assumptions", []), list) else 0
    calculation_count = len(packet.get("calculation_trace", [])) if isinstance(packet.get("calculation_trace", []), list) else 0
    review_flags = []
    if "knowledge-library" in missing and "site-intelligence" in missing and "catalyst-data" not in legacy_filled:
        review_flags.append("Evidence records are missing; import Knowledge Library or Site Intelligence evidence before external use.")
    if "workbench" in missing and "catalyst-finance" not in legacy_filled:
        review_flags.append("Technical calculation evidence is missing; import Workbench outputs before relying on modeled tradeoffs.")
    if "research-librarian" in missing:
        review_flags.append("Research route is missing; document unresolved questions and evidence gaps before final review.")
    if source_count == 0:
        review_flags.append("No explicit source ledger entries are attached yet.")
    return {
        "ok": True,
        "version": APP_VERSION,
        "decision_packet_version": APP_VERSION,
        "workflow_readiness_percent": readiness,
        "filled_modules": filled,
        "missing_modules": missing,
        "legacy_filled_modules": legacy_filled,
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
                "Attach Knowledge Library sources and citations for major claims.",
                "Import a Research Librarian route with evidence gaps and follow-up questions.",
                "Attach Site Intelligence observations and Research Lab validation where relevant.",
                "Use Workbench for calculations, graphs, sensitivity analysis, and technical review.",
            ],
        },
        "warnings": [
            "Module Artifact Adapters normalize user-provided JSON exports. They do not verify truth, source quality, professional compliance, or certification status.",
            "Decision Packet readiness is a review workflow aid, not approval, assurance, legal advice, financial advice, engineering review, ESG/SDG certification, or professional signoff.",
        ],
    }



def governance_state_catalog() -> Dict[str, Any]:
    return {
        "governance_version": APP_VERSION,
        "schema": GOVERNANCE_SCHEMA,
        "states": [
            {"id": "draft", "label": "Draft", "terminal": False},
            {"id": "evidence_gathering", "label": "Evidence gathering", "terminal": False},
            {"id": "analysis", "label": "Analysis", "terminal": False},
            {"id": "review", "label": "Review", "terminal": False},
            {"id": "revision_required", "label": "Revision required", "terminal": False},
            {"id": "approved", "label": "Approved", "terminal": False},
            {"id": "rejected", "label": "Rejected", "terminal": False},
            {"id": "deferred", "label": "Deferred", "terminal": False},
            {"id": "implemented", "label": "Implemented", "terminal": False},
            {"id": "retired", "label": "Retired", "terminal": True},
        ],
        "transitions": {
            "draft": ["evidence_gathering", "analysis", "deferred", "retired"],
            "evidence_gathering": ["analysis", "review", "revision_required", "deferred", "retired"],
            "analysis": ["evidence_gathering", "review", "revision_required", "deferred", "retired"],
            "review": ["revision_required", "approved", "rejected", "deferred"],
            "revision_required": ["evidence_gathering", "analysis", "review", "deferred", "retired"],
            "approved": ["implemented", "revision_required", "retired"],
            "rejected": ["revision_required", "retired"],
            "deferred": ["evidence_gathering", "analysis", "review", "retired"],
            "implemented": ["revision_required", "retired"],
            "retired": [],
        },
    }


def governance_template() -> Dict[str, Any]:
    return {
        "governance_version": APP_VERSION,
        "schema": GOVERNANCE_SCHEMA,
        "current_state": "draft",
        "decision_owner": {"name": "", "role": "", "organization": "", "accountable": True},
        "reviewers": [],
        "approval_conditions": [],
        "exceptions": [],
        "conflict_declarations": [],
        "signoffs": [],
        "review_history": [],
        "approval_expires_at": "",
        "reassessment_due_at": "",
        "transition_status": {"allowed": True, "requested_state": "draft", "blockers": []},
        "export_gate": {
            "internal_draft_allowed": True,
            "reviewed_export_allowed": False,
            "public_export_allowed": False,
            "professional_reliance_allowed": False,
            "blocking_reasons": ["Decision has not been approved by accountable human reviewers."],
        },
        "warnings": [
            "Decision Studio records governance actions but does not approve decisions autonomously.",
            "AI may flag gaps or contradictions but cannot provide sign-off, certification, assurance, or regulated professional approval.",
        ],
    }


def _record_status(item: Dict[str, Any], default: str = "open") -> str:
    return str(item.get("status", default)).strip().lower().replace(" ", "_")


def _governance_blockers(owner: Dict[str, Any], reviewers: List[Dict[str, Any]], conditions: List[Dict[str, Any]], exceptions: List[Dict[str, Any]], conflicts: List[Dict[str, Any]], signoffs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    blockers: List[Dict[str, Any]] = []
    if not str(owner.get("name", "")).strip():
        blockers.append({"code": "missing_decision_owner", "severity": "high", "message": "An accountable decision owner is required before approval."})
    for item in conditions:
        if bool(item.get("required", True)) and _record_status(item, "pending") not in {"satisfied", "waived"}:
            blockers.append({"code": "unsatisfied_approval_condition", "severity": str(item.get("severity", "high")), "record_id": item.get("condition_id", ""), "message": item.get("description", "Required approval condition is not satisfied.")})
    for item in exceptions:
        if _record_status(item) not in {"closed", "resolved", "accepted"} and str(item.get("severity", "medium")).lower() in {"critical", "high"}:
            blockers.append({"code": "open_material_exception", "severity": str(item.get("severity", "high")), "record_id": item.get("exception_id", ""), "message": item.get("description", "A material exception remains open.")})
    for item in conflicts:
        declared = bool(item.get("declared", True))
        mitigated = _record_status(item, "open") in {"mitigated", "resolved", "recused"} or bool(str(item.get("mitigation", "")).strip())
        if declared and not mitigated:
            blockers.append({"code": "unmitigated_conflict", "severity": "high", "record_id": item.get("conflict_id", ""), "message": item.get("description", "A declared conflict of interest has not been mitigated.")})
    reviewer_approvals = [r for r in reviewers if _record_status(r, "assigned") in {"approved", "accepted", "complete"}]
    signoff_roles = {str(s.get("role", "")).strip().lower().replace(" ", "_") for s in signoffs if _record_status(s, "signed") in {"signed", "approved", "accepted"}}
    if not reviewer_approvals:
        blockers.append({"code": "missing_reviewer_approval", "severity": "high", "message": "At least one assigned human reviewer must complete review before approval."})
    if "decision_owner" not in signoff_roles and "accountable_owner" not in signoff_roles:
        blockers.append({"code": "missing_owner_signoff", "severity": "high", "message": "The accountable decision owner has not signed off."})
    if not ({"governance_reviewer", "independent_reviewer", "review_chair"} & signoff_roles):
        blockers.append({"code": "missing_governance_signoff", "severity": "high", "message": "An independent governance or review sign-off is required."})
    return blockers


def _append_review_event(history: List[Dict[str, Any]], event_type: str, actor: str, actor_role: str, from_state: str, to_state: str, reason: str, details: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    ledger = [dict(item) for item in history if isinstance(item, dict)]
    previous_hash = str(ledger[-1].get("event_hash", "GENESIS")) if ledger else "GENESIS"
    event = {
        "event_schema": REVIEW_EVENT_SCHEMA,
        "sequence": len(ledger) + 1,
        "recorded_at": _utc_now(),
        "event_type": event_type,
        "actor": actor or "unspecified-human-actor",
        "actor_role": actor_role or "unspecified-role",
        "from_state": from_state,
        "to_state": to_state,
        "reason": reason,
        "details": details or {},
        "previous_hash": previous_hash,
    }
    event["event_hash"] = f"sha256:{_canonical_hash(event)}"
    ledger.append(event)
    return ledger


def verify_review_history(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    previous = "GENESIS"
    problems: List[Dict[str, Any]] = []
    for index, raw in enumerate(history):
        item = dict(raw) if isinstance(raw, dict) else {}
        supplied_hash = str(item.pop("event_hash", ""))
        if str(item.get("previous_hash", "")) != previous:
            problems.append({"sequence": index + 1, "code": "previous_hash_mismatch"})
        expected = f"sha256:{_canonical_hash(item)}"
        if supplied_hash != expected:
            problems.append({"sequence": index + 1, "code": "event_hash_mismatch"})
        previous = supplied_hash or expected
    return {"ok": not problems, "event_count": len(history), "problems": problems, "head_hash": previous}


def evaluate_governance(req: GovernanceRequest) -> Dict[str, Any]:
    packet = decision_packet_template()
    packet.update(req.packet or {})
    existing = packet.get("governance_center", {}) if isinstance(packet.get("governance_center"), dict) else {}
    current = str(req.currentState or existing.get("current_state") or "draft").strip().lower().replace(" ", "_")
    requested = str(req.requestedState or current).strip().lower().replace(" ", "_")
    catalog = governance_state_catalog()
    valid_states = {item["id"] for item in catalog["states"]}
    if current not in valid_states:
        current = "draft"
    owner = req.decisionOwner or existing.get("decision_owner") or {}
    reviewers = req.reviewers or existing.get("reviewers") or []
    conditions = req.approvalConditions or existing.get("approval_conditions") or []
    exceptions = req.exceptions or existing.get("exceptions") or []
    conflicts = req.conflictDeclarations or existing.get("conflict_declarations") or []
    signoffs = req.signoffs or existing.get("signoffs") or []
    history = req.reviewHistory or existing.get("review_history") or []
    transition_blockers: List[Dict[str, Any]] = []
    if requested not in valid_states:
        transition_blockers.append({"code": "unknown_state", "severity": "high", "message": f"Unknown requested state: {requested}"})
    elif requested != current and requested not in catalog["transitions"].get(current, []):
        transition_blockers.append({"code": "invalid_transition", "severity": "high", "message": f"Transition from {current} to {requested} is not allowed."})
    approval_blockers = _governance_blockers(owner, reviewers, conditions, exceptions, conflicts, signoffs)
    if requested in {"approved", "implemented"}:
        transition_blockers.extend(approval_blockers)
    allowed = not transition_blockers or req.forceTransition
    final_state = requested if allowed else current
    if requested != current:
        history = _append_review_event(
            history,
            "state_transition_forced" if req.forceTransition and transition_blockers else "state_transition",
            req.actor,
            req.actorRole,
            current,
            final_state,
            req.reason,
            {"blockers_at_transition": transition_blockers, "forced": req.forceTransition},
        )
    history_integrity = verify_review_history(history)
    export_blockers = list(approval_blockers)
    if final_state not in {"approved", "implemented"}:
        export_blockers.append({"code": "decision_not_approved", "severity": "high", "message": "Reviewed or public export requires an approved or implemented decision state."})
    if not history_integrity["ok"]:
        export_blockers.append({"code": "review_history_integrity_failed", "severity": "critical", "message": "The immutable review history hash chain did not verify."})
    confidential_open = any(bool(item.get("confidential", False)) and _record_status(item) not in {"closed", "resolved"} for item in exceptions)
    governance = {
        "governance_version": APP_VERSION,
        "schema": GOVERNANCE_SCHEMA,
        "current_state": final_state,
        "decision_owner": owner,
        "reviewers": reviewers,
        "approval_conditions": conditions,
        "exceptions": exceptions,
        "conflict_declarations": conflicts,
        "signoffs": signoffs,
        "review_history": history,
        "review_history_integrity": history_integrity,
        "approval_expires_at": req.approvalExpiresAt or existing.get("approval_expires_at", ""),
        "reassessment_due_at": req.reassessmentDueAt or existing.get("reassessment_due_at", ""),
        "transition_status": {"allowed": allowed, "from_state": current, "requested_state": requested, "final_state": final_state, "forced": req.forceTransition, "blockers": transition_blockers},
        "export_gate": {
            "internal_draft_allowed": final_state != "retired",
            "reviewed_export_allowed": final_state in {"approved", "implemented"} and not export_blockers,
            "public_export_allowed": final_state in {"approved", "implemented"} and not export_blockers and not confidential_open,
            "professional_reliance_allowed": False,
            "blocking_reasons": export_blockers,
        },
        "warnings": governance_template()["warnings"],
    }
    packet["governance_center"] = governance
    packet["saved_packet"] = {**packet.get("saved_packet", {}), "status": final_state}
    return {"ok": True, "version": APP_VERSION, "governance": governance, "decision_packet": packet, "state_catalog": catalog}



def collaboration_role_catalog() -> Dict[str, Any]:
    return {
        "schema": COLLABORATION_ROOM_SCHEMA,
        "roles": [
            {"id": "owner", "label": "Room owner", "permissions": ["manage_room", "manage_members", "comment", "request_change", "resolve", "snapshot", "apply_revision", "lock", "share"]},
            {"id": "facilitator", "label": "Facilitator", "permissions": ["manage_members", "comment", "request_change", "resolve", "snapshot", "apply_revision", "lock", "share"]},
            {"id": "editor", "label": "Editor", "permissions": ["comment", "request_change", "snapshot", "apply_revision"]},
            {"id": "reviewer", "label": "Reviewer", "permissions": ["comment", "request_change", "resolve", "snapshot"]},
            {"id": "client", "label": "Private client participant", "permissions": ["comment", "request_change"]},
            {"id": "observer", "label": "Observer", "permissions": []},
        ],
        "visibility": ["private", "restricted", "institutional"],
    }


def _room_permissions(role: str) -> List[str]:
    normalized = (role or "observer").strip().lower().replace("-", "_")
    aliases = {"decision_owner": "owner", "review_chair": "facilitator", "independent_reviewer": "reviewer"}
    normalized = aliases.get(normalized, normalized)
    for record in collaboration_role_catalog()["roles"]:
        if record["id"] == normalized:
            return list(record["permissions"])
    return []


def collaborative_room_template() -> Dict[str, Any]:
    return {
        "room_version": APP_VERSION,
        "schema": COLLABORATION_ROOM_SCHEMA,
        "event_schema": COLLABORATION_EVENT_SCHEMA,
        "room_id": "",
        "title": "Collaborative Decision Room",
        "visibility": "private",
        "status": "active",
        "owner": {},
        "members": [],
        "comments": [],
        "change_requests": [],
        "snapshots": [],
        "snapshot_comparisons": [],
        "activity_timeline": [],
        "activity_integrity": {"ok": True, "event_count": 0, "problems": [], "head_hash": "GENESIS"},
        "notifications": [],
        "share_grants": [],
        "locked_version": {},
        "contact_engagement_handoffs": [],
        "limits": {"members": 200, "comments": 2000, "change_requests": 500, "snapshots": 100, "activity_events": 5000},
        "canonical_persistence": "wordpress",
        "warnings": [
            "Decision Rooms are private collaboration records; WordPress authentication and authorization remain authoritative.",
            "Comments and approvals are human records. AI cannot approve, sign, certify, or impersonate a reviewer.",
            "Approved snapshots remain locked until an authorized human explicitly reopens the version with a reason.",
        ],
    }


def _room_id(prefix: str, value: Any) -> str:
    digest = hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _append_room_event(room: Dict[str, Any], event_type: str, actor: str, actor_role: str, target_type: str = "room", target_id: str = "", details: Optional[Dict[str, Any]] = None) -> None:
    timeline = list(room.get("activity_timeline") or [])
    previous = timeline[-1].get("event_hash", "GENESIS") if timeline else "GENESIS"
    event = {
        "event_schema": COLLABORATION_EVENT_SCHEMA,
        "sequence": len(timeline) + 1,
        "recorded_at": _utc_now(),
        "event_type": event_type,
        "actor": actor or "unspecified-human-actor",
        "actor_role": actor_role or "observer",
        "target_type": target_type,
        "target_id": target_id,
        "details": details or {},
        "previous_hash": previous,
    }
    event["event_hash"] = _canonical_hash(event)
    timeline.append(event)
    room["activity_timeline"] = timeline[-5000:]
    room["activity_integrity"] = verify_collaboration_history(room["activity_timeline"])


def verify_collaboration_history(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    previous = "GENESIS"
    problems: List[Dict[str, Any]] = []
    for index, raw in enumerate(history or []):
        item = dict(raw or {})
        supplied = str(item.pop("event_hash", ""))
        if str(item.get("previous_hash", "")) != previous:
            problems.append({"sequence": index + 1, "code": "previous_hash_mismatch"})
        expected = _canonical_hash(item)
        if supplied != expected:
            problems.append({"sequence": index + 1, "code": "event_hash_mismatch"})
        previous = supplied or expected
    return {"ok": not problems, "event_count": len(history or []), "problems": problems, "head_hash": previous}


def _packet_for_snapshot(packet: Dict[str, Any]) -> Dict[str, Any]:
    clone = json.loads(json.dumps(packet or {}, default=str))
    room = clone.get("collaboration_room")
    if isinstance(room, dict):
        clone["collaboration_room"] = {
            "room_id": room.get("room_id", ""),
            "schema": room.get("schema", COLLABORATION_ROOM_SCHEMA),
            "locked_version": room.get("locked_version", {}),
        }
    return clone


def _create_packet_snapshot(packet: Dict[str, Any], actor: str, label: str = "") -> Dict[str, Any]:
    content = _packet_for_snapshot(packet)
    content_hash = _canonical_hash(content)
    return {
        "snapshot_id": _room_id("snapshot", {"hash": content_hash, "actor": actor, "label": label, "at": _utc_now()}),
        "created_at": _utc_now(),
        "created_by": actor or "unspecified-human-actor",
        "label": label or "Decision Packet snapshot",
        "packet_version": packet.get("packet_version", APP_VERSION),
        "governance_state": _dig(packet, "governance_center", "current_state", default="draft"),
        "content_hash": content_hash,
        "packet": content,
        "locked": False,
    }


def _diff_values(before: Any, after: Any, path: str = "") -> List[Dict[str, Any]]:
    changes: List[Dict[str, Any]] = []
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            child = f"{path}.{key}" if path else str(key)
            if key not in before:
                changes.append({"path": child, "change": "added", "before": None, "after": after[key]})
            elif key not in after:
                changes.append({"path": child, "change": "removed", "before": before[key], "after": None})
            else:
                changes.extend(_diff_values(before[key], after[key], child))
    elif isinstance(before, list) and isinstance(after, list):
        if before != after:
            changes.append({"path": path or "$", "change": "changed", "before": before, "after": after})
    elif before != after:
        changes.append({"path": path or "$", "change": "changed", "before": before, "after": after})
    return changes[:1000]


def compare_room_snapshots(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    left = before.get("packet", before) if isinstance(before, dict) else {}
    right = after.get("packet", after) if isinstance(after, dict) else {}
    changes = _diff_values(left, right)
    return {
        "comparison_id": _room_id("comparison", {"before": before.get("content_hash", ""), "after": after.get("content_hash", "")}),
        "created_at": _utc_now(),
        "before_snapshot_id": before.get("snapshot_id", ""),
        "after_snapshot_id": after.get("snapshot_id", ""),
        "before_hash": before.get("content_hash", _canonical_hash(left)),
        "after_hash": after.get("content_hash", _canonical_hash(right)),
        "change_count": len(changes),
        "changed_paths": [item["path"] for item in changes],
        "changes": changes,
    }


def _merge_packet_patch(target: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    result = json.loads(json.dumps(target or {}, default=str))
    for key, value in (patch or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_packet_patch(result[key], value)
        else:
            result[key] = value
    return result


def _room_notify(room: Dict[str, Any], actor: str, event_type: str, target_id: str, message: str) -> None:
    notifications = list(room.get("notifications") or [])
    for member in room.get("members") or []:
        recipient = member.get("email") or member.get("user_id") or member.get("name")
        if not recipient or str(recipient) == str(actor):
            continue
        notifications.append({
            "notification_id": _room_id("notification", {"recipient": recipient, "event": event_type, "target": target_id, "at": _utc_now()}),
            "created_at": _utc_now(),
            "recipient": recipient,
            "event_type": event_type,
            "target_id": target_id,
            "message": message,
            "status": "pending",
        })
    room["notifications"] = notifications[-2000:]


def generate_collaborative_room(req: CollaborativeRoomRequest) -> Dict[str, Any]:
    packet = decision_packet_template()
    packet.update(req.packet or {})
    room = collaborative_room_template()
    existing = req.room or packet.get("collaboration_room") or {}
    if isinstance(existing, dict):
        room.update(existing)
    room["schema"] = COLLABORATION_ROOM_SCHEMA
    room["event_schema"] = COLLABORATION_EVENT_SCHEMA
    room["room_version"] = APP_VERSION
    room["room_id"] = room.get("room_id") or _room_id("room", {"title": room.get("title"), "actor": req.actor, "at": _utc_now()})
    room["visibility"] = room.get("visibility") if room.get("visibility") in {"private", "restricted", "institutional"} else "private"
    room["members"] = list(room.get("members") or [])[:200]
    room["comments"] = list(room.get("comments") or [])[:2000]
    room["change_requests"] = list(room.get("change_requests") or [])[:500]
    room["snapshots"] = list(room.get("snapshots") or [])[:100]
    room["snapshot_comparisons"] = list(room.get("snapshot_comparisons") or [])[:100]
    room["share_grants"] = list(room.get("share_grants") or [])[:500]
    action = (req.action or "evaluate").strip().lower().replace("-", "_")
    actor_role = (req.actorRole or "observer").strip().lower().replace("-", "_")
    permissions = _room_permissions(actor_role)
    payload = req.payload or {}
    result_extra: Dict[str, Any] = {}

    if not room.get("owner") and req.actor:
        room["owner"] = {"name": req.actor, "role": "owner"}
        if not room["members"]:
            room["members"].append({"member_id": _room_id("member", req.actor), "name": req.actor, "role": "owner", "status": "active"})

    def require_permission(permission: str) -> Optional[Dict[str, Any]]:
        if permission not in permissions:
            return {"ok": False, "version": APP_VERSION, "error": "collaboration_permission_denied", "required_permission": permission, "actor_role": actor_role, "room": room, "decision_packet": packet}
        return None

    if action == "add_comment":
        denied = require_permission("comment")
        if denied: return denied
        content = str(payload.get("content", "")).strip()
        if not content:
            return {"ok": False, "version": APP_VERSION, "error": "comment_content_required", "room": room, "decision_packet": packet}
        comment = {"comment_id": _room_id("comment", {"room": room["room_id"], "actor": req.actor, "content": content, "at": _utc_now()}), "created_at": _utc_now(), "author": req.actor or "unspecified-human-actor", "author_role": actor_role, "target_type": req.targetType or payload.get("target_type", "decision_packet"), "target_id": req.targetId or payload.get("target_id", ""), "content": content[:20000], "visibility": payload.get("visibility", "room"), "status": "open", "parent_comment_id": payload.get("parent_comment_id", "")}
        room["comments"].append(comment)
        _append_room_event(room, "comment_added", req.actor, actor_role, "comment", comment["comment_id"], {"target_type": comment["target_type"], "target_id": comment["target_id"]})
        _room_notify(room, req.actor, "comment_added", comment["comment_id"], f"New Decision Room comment from {comment['author']}.")
        result_extra["comment"] = comment
    elif action == "resolve_comment":
        denied = require_permission("resolve")
        if denied: return denied
        comment_id = str(payload.get("comment_id", "")) or req.targetId
        found = None
        for comment in room["comments"]:
            if comment.get("comment_id") == comment_id:
                comment["status"] = "resolved"
                comment["resolved_at"] = _utc_now()
                comment["resolved_by"] = req.actor
                comment["resolution"] = str(payload.get("resolution", req.reason))[:10000]
                found = comment
                break
        if not found: return {"ok": False, "version": APP_VERSION, "error": "comment_not_found", "room": room, "decision_packet": packet}
        _append_room_event(room, "comment_resolved", req.actor, actor_role, "comment", comment_id, {"resolution": found.get("resolution", "")})
        result_extra["comment"] = found
    elif action == "create_change_request":
        denied = require_permission("request_change")
        if denied: return denied
        title = str(payload.get("title", "Requested Decision Packet change")).strip()
        request_record = {"change_request_id": _room_id("change", {"room": room["room_id"], "actor": req.actor, "title": title, "at": _utc_now()}), "created_at": _utc_now(), "requested_by": req.actor or "unspecified-human-actor", "requested_by_role": actor_role, "title": title[:500], "description": str(payload.get("description", ""))[:20000], "target_type": req.targetType or payload.get("target_type", "decision_packet"), "target_id": req.targetId or payload.get("target_id", ""), "status": "open", "priority": payload.get("priority", "normal"), "packet_patch": payload.get("packet_patch", {}) if isinstance(payload.get("packet_patch"), dict) else {}, "resolution": {}}
        room["change_requests"].append(request_record)
        _append_room_event(room, "change_request_created", req.actor, actor_role, "change_request", request_record["change_request_id"], {"title": title})
        _room_notify(room, req.actor, "change_request_created", request_record["change_request_id"], f"New Decision Room change request: {title}.")
        result_extra["change_request"] = request_record
    elif action == "resolve_change_request":
        denied = require_permission("resolve")
        if denied: return denied
        change_id = str(payload.get("change_request_id", "")) or req.targetId
        resolution_status = str(payload.get("status", "accepted")).strip().lower()
        if resolution_status not in {"accepted", "rejected", "deferred", "implemented"}: resolution_status = "accepted"
        if resolution_status == "implemented" and room.get("locked_version", {}).get("locked"):
            return {"ok": False, "version": APP_VERSION, "error": "approved_version_locked", "room": room, "decision_packet": packet}
        found = None
        for item in room["change_requests"]:
            if item.get("change_request_id") == change_id:
                item["status"] = resolution_status
                item["resolved_at"] = _utc_now()
                item["resolved_by"] = req.actor
                item["resolution"] = {"reason": str(payload.get("resolution", req.reason))[:10000], "status": resolution_status}
                if resolution_status == "implemented" and isinstance(item.get("packet_patch"), dict):
                    before = _create_packet_snapshot(packet, req.actor, "Before implemented change request")
                    packet = _merge_packet_patch(packet, item["packet_patch"])
                    after = _create_packet_snapshot(packet, req.actor, "After implemented change request")
                    room["snapshots"].extend([before, after])
                    comparison = compare_room_snapshots(before, after)
                    room["snapshot_comparisons"].append(comparison)
                    result_extra["comparison"] = comparison
                found = item
                break
        if not found: return {"ok": False, "version": APP_VERSION, "error": "change_request_not_found", "room": room, "decision_packet": packet}
        _append_room_event(room, "change_request_resolved", req.actor, actor_role, "change_request", change_id, {"status": resolution_status})
        result_extra["change_request"] = found
    elif action in {"snapshot", "create_snapshot"}:
        denied = require_permission("snapshot")
        if denied: return denied
        current_hash = _canonical_hash(_packet_for_snapshot(packet))
        locked = room.get("locked_version", {})
        if locked.get("locked") and locked.get("content_hash") != current_hash:
            return {"ok": False, "version": APP_VERSION, "error": "approved_version_locked", "room": room, "decision_packet": packet}
        snapshot = _create_packet_snapshot(packet, req.actor, str(payload.get("label", "Decision Packet snapshot")))
        room["snapshots"].append(snapshot)
        _append_room_event(room, "snapshot_created", req.actor, actor_role, "snapshot", snapshot["snapshot_id"], {"content_hash": snapshot["content_hash"]})
        result_extra["snapshot"] = snapshot
    elif action == "compare_snapshots":
        snapshots = room["snapshots"]
        before = payload.get("before") if isinstance(payload.get("before"), dict) else (snapshots[-2] if len(snapshots) >= 2 else {})
        after = payload.get("after") if isinstance(payload.get("after"), dict) else (snapshots[-1] if snapshots else {})
        if not before or not after:
            return {"ok": False, "version": APP_VERSION, "error": "two_snapshots_required", "room": room, "decision_packet": packet}
        comparison = compare_room_snapshots(before, after)
        room["snapshot_comparisons"].append(comparison)
        _append_room_event(room, "snapshots_compared", req.actor, actor_role, "comparison", comparison["comparison_id"], {"change_count": comparison["change_count"]})
        result_extra["comparison"] = comparison
    elif action == "apply_revision":
        denied = require_permission("apply_revision")
        if denied: return denied
        if room.get("locked_version", {}).get("locked"):
            return {"ok": False, "version": APP_VERSION, "error": "approved_version_locked", "room": room, "decision_packet": packet}
        patch = payload.get("packet_patch", {}) if isinstance(payload.get("packet_patch"), dict) else {}
        if not patch: return {"ok": False, "version": APP_VERSION, "error": "packet_patch_required", "room": room, "decision_packet": packet}
        before = _create_packet_snapshot(packet, req.actor, "Before revision")
        packet = _merge_packet_patch(packet, patch)
        after = _create_packet_snapshot(packet, req.actor, "After revision")
        room["snapshots"].extend([before, after])
        comparison = compare_room_snapshots(before, after)
        room["snapshot_comparisons"].append(comparison)
        _append_room_event(room, "packet_revision_applied", req.actor, actor_role, "comparison", comparison["comparison_id"], {"reason": req.reason, "change_count": comparison["change_count"]})
        result_extra["comparison"] = comparison
    elif action == "invite_member":
        denied = require_permission("manage_members")
        if denied: return denied
        if len(room["members"]) >= 200: return {"ok": False, "version": APP_VERSION, "error": "room_member_limit_reached", "room": room, "decision_packet": packet}
        member = payload.get("member", {}) if isinstance(payload.get("member"), dict) else payload
        email = str(member.get("email", "")).strip().lower()
        name = str(member.get("name", email or "Invited participant")).strip()
        member_role = str(member.get("role", "observer")).strip().lower()
        token = secrets.token_urlsafe(24)
        member_record = {"member_id": _room_id("member", {"room": room["room_id"], "email": email, "name": name}), "user_id": member.get("user_id", ""), "email": email, "name": name, "role": member_role, "status": "invited", "invited_at": _utc_now(), "invited_by": req.actor}
        room["members"].append(member_record)
        grant = {"grant_id": _room_id("grant", {"room": room["room_id"], "member": member_record["member_id"], "at": _utc_now()}), "member_id": member_record["member_id"], "role": member_role, "status": "active", "expires_at": str(member.get("expires_at", "")), "token_hash": "sha256:" + hashlib.sha256(token.encode("utf-8")).hexdigest(), "token_hint": token[:4] + "…" + token[-4:]}
        room["share_grants"].append(grant)
        _append_room_event(room, "member_invited", req.actor, actor_role, "member", member_record["member_id"], {"role": member_role})
        result_extra["member"] = member_record
        result_extra["share_grant"] = grant
        result_extra["share_token_once"] = token
    elif action == "lock_version":
        denied = require_permission("lock")
        if denied: return denied
        governance_state = _dig(packet, "governance_center", "current_state", default="draft")
        if governance_state not in {"approved", "implemented"}:
            return {"ok": False, "version": APP_VERSION, "error": "governance_approval_required", "governance_state": governance_state, "room": room, "decision_packet": packet}
        snapshot = _create_packet_snapshot(packet, req.actor, str(payload.get("label", "Approved Decision Packet")))
        snapshot["locked"] = True
        room["snapshots"].append(snapshot)
        room["locked_version"] = {"locked": True, "snapshot_id": snapshot["snapshot_id"], "content_hash": snapshot["content_hash"], "locked_at": _utc_now(), "locked_by": req.actor, "governance_state": governance_state}
        room["status"] = "locked"
        _append_room_event(room, "approved_version_locked", req.actor, actor_role, "snapshot", snapshot["snapshot_id"], {"content_hash": snapshot["content_hash"], "governance_state": governance_state})
        result_extra["snapshot"] = snapshot
    elif action == "reopen_version":
        denied = require_permission("lock")
        if denied: return denied
        if not str(req.reason or payload.get("reason", "")).strip():
            return {"ok": False, "version": APP_VERSION, "error": "reopen_reason_required", "room": room, "decision_packet": packet}
        previous_lock = dict(room.get("locked_version") or {})
        room["locked_version"] = {"locked": False, "reopened_at": _utc_now(), "reopened_by": req.actor, "reason": req.reason or payload.get("reason", ""), "previous_lock": previous_lock}
        room["status"] = "active"
        _append_room_event(room, "approved_version_reopened", req.actor, actor_role, "room", room["room_id"], {"reason": req.reason or payload.get("reason", "")})
    elif action == "contact_handoff":
        denied = require_permission("share")
        if denied: return denied
        handoff = {"schema": "sc-contact-engagement-handoff/1.0", "handoff_id": _room_id("engagement", {"room": room["room_id"], "at": _utc_now()}), "created_at": _utc_now(), "source_product": "decision-studio", "source_version": APP_VERSION, "decision_room_id": room["room_id"], "project_name": _dig(packet, "project", "project_name", default=""), "decision_question": _dig(packet, "project", "decision_question", default=""), "participants": [{"name": m.get("name", ""), "email": m.get("email", ""), "role": m.get("role", "observer")} for m in room.get("members", [])], "collaboration_needs": payload.get("collaboration_needs", []), "private_workspace_required": True, "requested_next_action": payload.get("requested_next_action", "Create or connect a private engagement workspace."), "notes": str(payload.get("notes", ""))[:20000]}
        room["contact_engagement_handoffs"].append(handoff)
        _append_room_event(room, "contact_engagement_handoff_created", req.actor, actor_role, "handoff", handoff["handoff_id"], {"requested_next_action": handoff["requested_next_action"]})
        result_extra["contact_engagement_handoff"] = handoff
    elif action not in {"evaluate", "create", "save"}:
        return {"ok": False, "version": APP_VERSION, "error": "unknown_collaboration_action", "action": action, "room": room, "decision_packet": packet}

    room["metrics"] = {"member_count": len(room["members"]), "open_comment_count": sum(1 for item in room["comments"] if item.get("status") == "open"), "open_change_request_count": sum(1 for item in room["change_requests"] if item.get("status") == "open"), "snapshot_count": len(room["snapshots"]), "pending_notification_count": sum(1 for item in room.get("notifications", []) if item.get("status") == "pending")}
    room["activity_integrity"] = verify_collaboration_history(room.get("activity_timeline", []))
    packet["packet_version"] = APP_VERSION
    packet["collaboration_room_schema"] = COLLABORATION_ROOM_SCHEMA
    packet["collaboration_event_schema"] = COLLABORATION_EVENT_SCHEMA
    packet["collaboration_room"] = room
    return {"ok": True, "version": APP_VERSION, "schema": COLLABORATION_ROOM_SCHEMA, "room": room, "decision_packet": packet, "actor_permissions": permissions, **result_extra}

def review_status_catalog() -> Dict[str, Any]:
    """Review state vocabulary used by v1.12.0 readiness and scenario governance gates."""
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
        {"id": "framing", "label": "Decision Framing", "module_id": "decision-studio", "weight": 10, "required": True, "expert_review": False},
        {"id": "evidence", "label": "Evidence & Sources", "module_id": "knowledge-library", "weight": 16, "required": True, "expert_review": False},
        {"id": "scenarios", "label": "Scenario & Model Evidence", "module_id": "workbench", "weight": 10, "required": False, "expert_review": False},
        {"id": "impact", "label": "Live & Experimental Evidence", "module_id": "site-intelligence", "weight": 12, "required": True, "expert_review": False},
        {"id": "claims", "label": "Research Gaps & Claims", "module_id": "research-librarian", "weight": 12, "required": True, "expert_review": True},
        {"id": "finance", "label": "Calculated Tradeoffs", "module_id": "workbench", "weight": 14, "required": True, "expert_review": True},
        {"id": "recovery", "label": "Entities & Provenance", "module_id": "platform-core", "weight": 8, "required": False, "expert_review": False},
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
        return packet.get("evidence_registry") or packet.get("live_evidence") or records or packet.get("evidence_records") or packet.get("sources") or audit.get("source_ledger")
    if sid == "scenarios":
        records = packet.get("scenarios", {}).get("records", []) if isinstance(packet.get("scenarios", {}), dict) else []
        return records or packet.get("scenario_analysis") or packet.get("workbench_calculations") or packet.get("technical_artifacts") or results.get("scenarios")
    if sid == "impact":
        records = packet.get("impact_measurement", {}).get("records", []) if isinstance(packet.get("impact_measurement", {}), dict) else []
        return packet.get("live_evidence") or packet.get("experimental_evidence") or records or packet.get("impact_records")
    if sid == "claims":
        records = packet.get("claim_and_risk_review", {}).get("records", []) if isinstance(packet.get("claim_and_risk_review", {}), dict) else []
        return packet.get("evidence_gaps") or packet.get("research_routes") or records or packet.get("claim_reviews") or audit.get("claim_trace")
    if sid == "finance":
        return packet.get("financial_tradeoffs") or packet.get("finance_analysis") or results.get("finance")
    if sid == "recovery":
        return packet.get("platform_registry") or packet.get("entities") or packet.get("provenance_links") or packet.get("execution_and_recovery") or packet.get("execution_recovery")
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
    for key in ("evidence_registry", "live_evidence", "experimental_evidence", "evidence_ledger"):
        if isinstance(packet.get(key), list):
            count += len(packet.get(key, []))
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
                flags.append({"severity": "high", "section": sid, "issue": "Decision question is missing.", "action": "Complete the intake decision question or import a compatible framing artifact."})
        elif sid == "evidence":
            if source_count:
                score += min(25, source_count * 8)
            else:
                flags.append({"severity": "critical", "section": sid, "issue": "No source or evidence records are attached.", "action": "Import Knowledge Library or Site Intelligence evidence, or add source-ledger entries."})
            if float(inputs.dataConfidence or 0) < 60:
                flags.append({"severity": "high", "section": sid, "issue": "Data confidence is below 60.", "action": "Document source quality, method notes, and review status."})
        elif sid == "scenarios":
            if present:
                score += 25
            else:
                score = 35
                flags.append({"severity": "medium", "section": sid, "issue": "No imported scenario artifact is attached.", "action": "Import Workbench model outputs or use Decision Studio's built-in scenario screen as a draft."})
        elif sid == "impact":
            if present:
                score += 25
            else:
                flags.append({"severity": "high", "section": sid, "issue": "Impact record is missing.", "action": "Import Site Intelligence observations or Research Lab experimental evidence."})
        elif sid == "claims":
            if present:
                score += 20
            else:
                flags.append({"severity": "high", "section": sid, "issue": "Claim review is missing.", "action": "Import Research Librarian evidence gaps and review claims before publication."})
        elif sid == "finance":
            if present:
                score += 15
            if inputs.capex > 0 and inputs.annualSavings > 0:
                score += 15
            else:
                flags.append({"severity": "high", "section": sid, "issue": "Finance assumptions are incomplete.", "action": "Enter CAPEX and annual savings or import Workbench calculation evidence."})
            if assumptions_count == 0:
                flags.append({"severity": "medium", "section": sid, "issue": "No imported assumptions register is attached.", "action": "Import Workbench assumptions or generate audit/provenance before final export."})
        elif sid == "recovery":
            if present:
                score += 30
            else:
                score = 35
                flags.append({"severity": "medium", "section": sid, "issue": "Execution/recovery artifact is missing.", "action": "Import Platform Core entities and provenance links for cross-product traceability."})
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
            "Evidence/source review" if source_count else "Evidence/source review required before export",
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
        "scenario_studio_schema": SCENARIO_STUDIO_SCHEMA,
        "collaboration_room_schema": COLLABORATION_ROOM_SCHEMA,
        "collaboration_event_schema": COLLABORATION_EVENT_SCHEMA,
        "advanced_studio_available": True,
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



def scenario_studio_criteria() -> List[Dict[str, Any]]:
    return [
        {"id": "financial_value", "label": "Financial value", "metric": "npv", "weight": 20, "direction": "higher", "normalization": "financial"},
        {"id": "emissions_impact", "label": "Emissions impact", "metric": "annual_avoided_tco2e", "weight": 18, "direction": "higher", "normalization": "emissions"},
        {"id": "risk_resilience", "label": "Risk and resilience", "metric": "risk_score", "weight": 16, "direction": "lower", "normalization": "risk"},
        {"id": "evidence_confidence", "label": "Evidence confidence", "metric": "confidence", "weight": 10, "direction": "higher", "normalization": "score"},
        {"id": "stakeholder_equity", "label": "Stakeholder and distributional impact", "metric": "stakeholder_equity", "weight": 10, "direction": "higher", "normalization": "score"},
        {"id": "implementation_feasibility", "label": "Implementation feasibility", "metric": "implementation_feasibility", "weight": 10, "direction": "higher", "normalization": "score"},
        {"id": "reversibility", "label": "Reversibility and option value", "metric": "reversibility", "weight": 8, "direction": "higher", "normalization": "score"},
        {"id": "time_to_value", "label": "Time to value", "metric": "payback_years", "weight": 8, "direction": "lower", "normalization": "payback"},
    ]


def scenario_studio_template() -> Dict[str, Any]:
    return {
        "schema": SCENARIO_STUDIO_SCHEMA,
        "studio_version": APP_VERSION,
        "alternative_limit": 100,
        "default_alternatives": ["Baseline", "Conservative", "Expected", "Ambitious", "Stress Test"],
        "criteria": scenario_studio_criteria(),
        "supported_parameters": [
            "capex", "annualSavings", "discountRate", "modelYears", "baselineEmissions",
            "reductionRate", "adoptionRate", "exposure", "vulnerability", "resilience",
            "stakeholderSensitivity", "governanceReadiness", "dataConfidence", "socialBenefit",
            "carbonPrice", "reversibility", "stakeholderEquity", "implementationComplexity",
        ],
        "supported_metrics": [
            "decision_score", "npv", "roi_percent", "payback_years", "annual_avoided_tco2e",
            "total_avoided_tco2e", "risk_score", "confidence", "stakeholder_equity",
            "implementation_feasibility", "reversibility", "option_value",
        ],
        "analyses": [
            "weighted and unweighted ranking", "one-way sensitivity", "two-variable screening grid",
            "threshold and break-even search", "uncertainty envelopes", "time-horizon comparison",
            "stakeholder distribution", "dominance and tradeoff analysis", "reversibility and option value",
        ],
        "workbench_boundary": "Decision Studio provides deterministic screening and comparison. Route probabilistic simulation, optimization, engineering models, and domain-specific forecasting to Workbench.",
        "warnings": [
            "Scenario outputs are conditional decision-support results, not forecasts or guarantees.",
            "Ranges describe assumptions supplied by the user; they are not probability distributions unless modeled and validated elsewhere.",
        ],
    }


def _scenario_default_alternatives(inputs: DecisionInputs) -> List[Dict[str, Any]]:
    return [
        {"id": "baseline", "label": "Baseline", "parameters": {"reductionRate": 0, "adoptionRate": 0, "annualSavings": 0, "capex": 0}, "reversibility": 90, "stakeholderEquity": 45, "implementationComplexity": "Low"},
        {"id": "conservative", "label": "Conservative", "parameters": {"reductionRate": inputs.reductionRate * .75, "adoptionRate": inputs.adoptionRate * .80, "annualSavings": inputs.annualSavings * .80, "capex": inputs.capex * 1.10}, "reversibility": 75, "stakeholderEquity": max(0, inputs.socialBenefit - 5), "implementationComplexity": "Low"},
        {"id": "expected", "label": "Expected", "parameters": {}, "reversibility": 60, "stakeholderEquity": inputs.socialBenefit, "implementationComplexity": inputs.complexity},
        {"id": "ambitious", "label": "Ambitious", "parameters": {"reductionRate": min(100, inputs.reductionRate * 1.30), "adoptionRate": min(100, inputs.adoptionRate * 1.20), "annualSavings": inputs.annualSavings * 1.12, "capex": inputs.capex * 1.18}, "reversibility": 40, "stakeholderEquity": min(100, inputs.socialBenefit + 8), "implementationComplexity": "High"},
        {"id": "stress-test", "label": "Stress Test", "parameters": {"reductionRate": inputs.reductionRate * .65, "adoptionRate": inputs.adoptionRate * .65, "annualSavings": inputs.annualSavings * .65, "capex": inputs.capex * 1.25, "exposure": min(100, inputs.exposure + 15), "vulnerability": min(100, inputs.vulnerability + 15), "governanceReadiness": max(0, inputs.governanceReadiness - 15)}, "reversibility": 45, "stakeholderEquity": max(0, inputs.socialBenefit - 10), "implementationComplexity": "High"},
    ]


def _scenario_parameter_ranges(inputs: DecisionInputs, supplied: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    defaults: Dict[str, Dict[str, Any]] = {
        "capex": {"min": max(0, inputs.capex * (1 - inputs.capexVolatility / 100)), "max": inputs.capex * (1 + inputs.capexVolatility / 100), "steps": 5},
        "annualSavings": {"min": max(0, inputs.annualSavings * (1 - inputs.savingsVolatility / 100)), "max": inputs.annualSavings * (1 + inputs.savingsVolatility / 100), "steps": 5},
        "adoptionRate": {"min": max(0, inputs.adoptionRate - 15), "max": min(100, inputs.adoptionRate + 15), "steps": 5},
        "reductionRate": {"min": max(0, inputs.reductionRate - 12), "max": min(100, inputs.reductionRate + 12), "steps": 5},
        "discountRate": {"min": max(0, inputs.discountRate - 3), "max": min(100, inputs.discountRate + 3), "steps": 5},
    }
    for key, raw in (supplied or {}).items():
        if isinstance(raw, (list, tuple)) and len(raw) >= 2:
            low, high = _numeric(raw[0]), _numeric(raw[1])
            steps = 5
        elif isinstance(raw, dict):
            low, high = _numeric(raw.get("min", raw.get("low"))), _numeric(raw.get("max", raw.get("high")))
            steps = int(_numeric(raw.get("steps"), 5) or 5)
        else:
            continue
        if low is None or high is None:
            continue
        if low > high:
            low, high = high, low
        defaults[str(key)] = {"min": low, "max": high, "steps": max(3, min(21, steps))}
    return defaults


def _scenario_linspace(low: float, high: float, points: int) -> List[float]:
    if points <= 1 or low == high:
        return [round(low, 8)]
    return [round(low + (high - low) * idx / (points - 1), 8) for idx in range(points)]


def _scenario_complexity_score(value: Any) -> float:
    text = str(value or "medium").strip().lower()
    return 88.0 if text in {"low", "simple"} else 65.0 if text in {"medium", "moderate"} else 42.0


def _scenario_stakeholder_summary(alternative: Dict[str, Any], inputs: DecisionInputs) -> Dict[str, Any]:
    records = alternative.get("stakeholder_impacts", alternative.get("stakeholderImpacts", []))
    normalized: List[Dict[str, Any]] = []
    if isinstance(records, list):
        for idx, record in enumerate(records):
            if not isinstance(record, dict):
                continue
            score = clamp(_numeric(record.get("impact_score", record.get("score")), inputs.socialBenefit) or 0)
            weight = max(0, _numeric(record.get("weight"), 1) or 1)
            normalized.append({
                "stakeholder": _first_present(record.get("stakeholder"), record.get("group"), default=f"Group {idx + 1}"),
                "impact_score": round(score, 2), "weight": round(weight, 4),
                "notes": str(record.get("notes", "")),
            })
    explicit = _numeric(alternative.get("stakeholderEquity", alternative.get("stakeholder_equity")), None)
    if normalized:
        total_weight = sum(item["weight"] for item in normalized) or len(normalized)
        average = sum(item["impact_score"] * item["weight"] for item in normalized) / total_weight
        minimum = min(item["impact_score"] for item in normalized)
        maximum = max(item["impact_score"] for item in normalized)
        equity = clamp((average * .70) + (minimum * .30))
    else:
        equity = clamp(explicit if explicit is not None else inputs.socialBenefit)
        average = minimum = maximum = equity
    return {"records": normalized, "weighted_average": round(average, 2), "minimum_group_score": round(minimum, 2), "maximum_group_score": round(maximum, 2), "equity_score": round(equity, 2)}


def _scenario_model(inputs: DecisionInputs, alternative: Dict[str, Any], extra: Optional[Dict[str, Any]] = None) -> tuple[DecisionInputs, Dict[str, Any]]:
    data = inputs.model_dump()
    params: Dict[str, Any] = {}
    if isinstance(alternative.get("parameters"), dict):
        params.update(alternative["parameters"])
    for key in list(data):
        if key in alternative:
            params[key] = alternative[key]
    if extra:
        params.update(extra)
    aliases = {"implementation_complexity": "complexity", "implementationComplexity": "complexity"}
    for key, value in list(params.items()):
        target = aliases.get(key, key)
        if target in data and value not in (None, ""):
            data[target] = value
    # Keep user-supplied screening values inside the DecisionInputs boundaries.
    for key in ["reductionRate", "adoptionRate", "discountRate", "exposure", "vulnerability", "resilience", "stakeholderSensitivity", "governanceReadiness", "dataConfidence", "socialBenefit", "savingsVolatility", "capexVolatility"]:
        if key in data:
            data[key] = clamp(_numeric(data[key], getattr(inputs, key)) or 0)
    for key in ["baselineEmissions", "capex", "annualSavings", "carbonPrice"]:
        if key in data:
            data[key] = max(0, _numeric(data[key], getattr(inputs, key)) or 0)
    data["modelYears"] = max(1, min(50, int(_numeric(data.get("modelYears"), inputs.modelYears) or inputs.modelYears)))
    model = DecisionInputs(**data)
    return model, analyze(model)


def _scenario_raw_evaluation(inputs: DecisionInputs, alternative: Dict[str, Any], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    model, results = _scenario_model(inputs, alternative, extra)
    stakeholder = _scenario_stakeholder_summary(alternative, model)
    reversibility = clamp(_numeric(alternative.get("reversibility"), 55) or 55)
    complexity = alternative.get("implementationComplexity", alternative.get("implementation_complexity", model.complexity))
    feasibility = clamp((_scenario_complexity_score(complexity) * .55) + (model.governanceReadiness * .30) + (model.dataConfidence * .15))
    payback = results.get("finance", {}).get("payback_years")
    payback_score = 50 if payback is None else clamp(100 - (float(payback) / max(model.modelYears, 1)) * 70)
    npv_value = _numeric(results.get("finance", {}).get("npv"), 0) or 0
    financial_score = clamp(50 + (npv_value / max(model.capex, 1)) * 35)
    annual = _numeric(results.get("emissions", {}).get("annual_avoided_tco2e"), 0) or 0
    emissions_score = clamp(annual / max(model.baselineEmissions, 1) * 100)
    risk_score = clamp(100 - (_numeric(results.get("risk", {}).get("risk_score"), 50) or 50))
    option_value = clamp(reversibility * .65 + feasibility * .20 + model.dataConfidence * .15)
    return {
        "alternative_id": str(alternative.get("id", alternative.get("option_id", "alternative"))),
        "label": _first_present(alternative.get("label"), alternative.get("name"), default="Alternative"),
        "description": str(alternative.get("description", alternative.get("notes", ""))),
        "parameters": model.model_dump(),
        "results": results,
        "metrics": {
            "npv": npv_value,
            "roi_percent": _numeric(results.get("finance", {}).get("roi_percent"), 0) or 0,
            "payback_years": payback,
            "annual_avoided_tco2e": annual,
            "total_avoided_tco2e": _numeric(results.get("emissions", {}).get("total_avoided_tco2e"), 0) or 0,
            "risk_score": _numeric(results.get("risk", {}).get("risk_score"), 50) or 50,
            "confidence": model.dataConfidence,
            "stakeholder_equity": stakeholder["equity_score"],
            "implementation_feasibility": round(feasibility, 2),
            "reversibility": round(reversibility, 2),
            "option_value": round(option_value, 2),
        },
        "criterion_scores": {
            "financial_value": round(financial_score, 2),
            "emissions_impact": round(emissions_score, 2),
            "risk_resilience": round(risk_score, 2),
            "evidence_confidence": round(model.dataConfidence, 2),
            "stakeholder_equity": stakeholder["equity_score"],
            "implementation_feasibility": round(feasibility, 2),
            "reversibility": round(reversibility, 2),
            "time_to_value": round(payback_score, 2),
        },
        "stakeholder_distribution": stakeholder,
        "implementation_complexity": complexity,
    }


def _scenario_apply_criteria(evaluation: Dict[str, Any], criteria: List[Dict[str, Any]]) -> Dict[str, Any]:
    criterion_scores = dict(evaluation.get("criterion_scores", {}))
    custom_values = evaluation.get("custom_criteria", {})
    rows: List[Dict[str, Any]] = []
    total_weight = sum(max(0, _numeric(item.get("weight"), 0) or 0) for item in criteria) or 1
    weighted = 0.0
    score_values: List[float] = []
    for criterion in criteria:
        cid = str(criterion.get("id", criterion.get("metric", "criterion")))
        metric = str(criterion.get("metric", cid))
        score = criterion_scores.get(cid)
        if score is None:
            raw = _numeric(evaluation.get("metrics", {}).get(metric), None)
            if raw is None:
                raw = _numeric(custom_values.get(cid), _numeric(criterion.get("default"), 50))
            low = _numeric(criterion.get("min"), 0) or 0
            high = _numeric(criterion.get("max"), 100) or 100
            if high == low:
                score = 50.0
            else:
                score = clamp((float(raw) - low) / (high - low) * 100)
                if str(criterion.get("direction", "higher")).lower() == "lower":
                    score = 100 - score
        score = clamp(float(score))
        weight = max(0, _numeric(criterion.get("weight"), 0) or 0)
        weighted += score * weight / total_weight
        score_values.append(score)
        rows.append({"criterion_id": cid, "label": criterion.get("label", cid), "metric": metric, "weight": round(weight / total_weight * 100, 4), "score": round(score, 2), "weighted_contribution": round(score * weight / total_weight, 2)})
    result = dict(evaluation)
    result["criteria"] = rows
    result["decision_score"] = round(clamp(weighted), 2)
    result["unweighted_score"] = round(sum(score_values) / len(score_values), 2) if score_values else 0
    return result


def _scenario_metric(evaluation: Dict[str, Any], metric: str) -> Optional[float]:
    if metric == "decision_score":
        return _numeric(evaluation.get("decision_score"), None)
    return _numeric(evaluation.get("metrics", {}).get(metric), None)


def _scenario_evaluate(inputs: DecisionInputs, alternative: Dict[str, Any], criteria: List[Dict[str, Any]], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    evaluation = _scenario_raw_evaluation(inputs, alternative, extra)
    evaluation["custom_criteria"] = alternative.get("criteria_values", alternative.get("criteriaValues", {})) if isinstance(alternative, dict) else {}
    return _scenario_apply_criteria(evaluation, criteria)


def _scenario_rank(evaluations: List[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
    ordered = sorted(evaluations, key=lambda item: _numeric(item.get(key), 0) or 0, reverse=True)
    return [{"rank": idx, "alternative_id": item["alternative_id"], "label": item["label"], "score": item.get(key)} for idx, item in enumerate(ordered, 1)]


def _scenario_dominance(evaluations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for left in evaluations:
        dominated: List[str] = []
        left_scores = {r["criterion_id"]: r["score"] for r in left.get("criteria", [])}
        for right in evaluations:
            if left is right:
                continue
            right_scores = {r["criterion_id"]: r["score"] for r in right.get("criteria", [])}
            shared = set(left_scores) & set(right_scores)
            if shared and all(left_scores[k] >= right_scores[k] for k in shared) and any(left_scores[k] > right_scores[k] for k in shared):
                dominated.append(right["alternative_id"])
        rows.append({"alternative_id": left["alternative_id"], "dominates": dominated, "dominated_count": len(dominated)})
    return rows


def _scenario_one_way(inputs: DecisionInputs, alternative: Dict[str, Any], criteria: List[Dict[str, Any]], ranges: Dict[str, Dict[str, Any]], parameters: List[str], grid_points: int) -> Dict[str, Any]:
    series: List[Dict[str, Any]] = []
    for parameter in parameters:
        if parameter not in ranges:
            continue
        spec = ranges[parameter]
        points = max(3, min(21, int(spec.get("steps", grid_points) or grid_points)))
        values = _scenario_linspace(float(spec["min"]), float(spec["max"]), points)
        observations = []
        for value in values:
            evaluated = _scenario_evaluate(inputs, alternative, criteria, {parameter: value})
            observations.append({"parameter_value": value, "decision_score": evaluated["decision_score"], "npv": evaluated["metrics"]["npv"], "annual_avoided_tco2e": evaluated["metrics"]["annual_avoided_tco2e"], "risk_score": evaluated["metrics"]["risk_score"]})
        scores = [item["decision_score"] for item in observations]
        series.append({"parameter": parameter, "min": spec["min"], "max": spec["max"], "observations": observations, "score_range": round(max(scores) - min(scores), 2), "most_sensitive": False})
    if series:
        biggest = max(series, key=lambda item: item["score_range"])
        biggest["most_sensitive"] = True
    return {"parameters": series, "tornado_ranking": sorted([{"parameter": item["parameter"], "score_range": item["score_range"]} for item in series], key=lambda item: item["score_range"], reverse=True)}


def _scenario_multi_variable(inputs: DecisionInputs, alternative: Dict[str, Any], criteria: List[Dict[str, Any]], ranges: Dict[str, Dict[str, Any]], parameters: List[str]) -> Dict[str, Any]:
    selected = [p for p in parameters if p in ranges][:2]
    if len(selected) < 2:
        return {"parameters": selected, "grid": [], "note": "At least two ranged parameters are required."}
    x, y = selected
    x_values = _scenario_linspace(float(ranges[x]["min"]), float(ranges[x]["max"]), 3)
    y_values = _scenario_linspace(float(ranges[y]["min"]), float(ranges[y]["max"]), 3)
    grid = []
    for xv in x_values:
        for yv in y_values:
            evaluated = _scenario_evaluate(inputs, alternative, criteria, {x: xv, y: yv})
            grid.append({x: xv, y: yv, "decision_score": evaluated["decision_score"], "npv": evaluated["metrics"]["npv"], "risk_score": evaluated["metrics"]["risk_score"]})
    return {"parameters": selected, "x_values": x_values, "y_values": y_values, "grid": grid, "screening_only": True}


def _scenario_threshold(inputs: DecisionInputs, alternative: Dict[str, Any], criteria: List[Dict[str, Any]], ranges: Dict[str, Dict[str, Any]], target: Dict[str, Any], grid_points: int) -> Dict[str, Any]:
    parameter = str(target.get("parameter", "annualSavings"))
    metric = str(target.get("metric", "npv"))
    operator = str(target.get("operator", ">="))
    target_value = _numeric(target.get("value"), 0) or 0
    spec = ranges.get(parameter)
    if not spec:
        base = _numeric(getattr(inputs, parameter, None), 0) or 0
        spec = {"min": max(0, base * .25), "max": max(1, base * 2), "steps": grid_points}
    values = _scenario_linspace(float(spec["min"]), float(spec["max"]), max(5, min(101, grid_points * 5)))
    observations: List[Dict[str, Any]] = []
    crossing = None
    for value in values:
        evaluated = _scenario_evaluate(inputs, alternative, criteria, {parameter: value})
        metric_value = _scenario_metric(evaluated, metric)
        met = False if metric_value is None else (metric_value >= target_value if operator in {">=", ">"} else metric_value <= target_value)
        row = {"parameter_value": value, "metric_value": metric_value, "target_met": met}
        observations.append(row)
        if met and crossing is None:
            crossing = row
    return {"parameter": parameter, "metric": metric, "operator": operator, "target_value": target_value, "range": spec, "break_even": crossing, "observations": observations, "found": crossing is not None, "screening_resolution": len(values)}


def _scenario_time_horizons(inputs: DecisionInputs, alternative: Dict[str, Any], criteria: List[Dict[str, Any]], horizons: List[int]) -> List[Dict[str, Any]]:
    output = []
    for horizon in sorted(set(max(1, min(50, int(h))) for h in horizons)):
        evaluated = _scenario_evaluate(inputs, alternative, criteria, {"modelYears": horizon})
        output.append({"years": horizon, "decision_score": evaluated["decision_score"], "npv": evaluated["metrics"]["npv"], "total_avoided_tco2e": evaluated["metrics"]["total_avoided_tco2e"], "payback_years": evaluated["metrics"]["payback_years"]})
    return output


def generate_scenario_studio(req: ScenarioStudioRequest, mode: str = "full") -> Dict[str, Any]:
    inputs = req.inputs
    packet = req.packet or {}
    alternatives = [item for item in req.alternatives if isinstance(item, dict)] or _scenario_default_alternatives(inputs)
    criteria = [item for item in req.criteria if isinstance(item, dict)] or scenario_studio_criteria()
    ranges = _scenario_parameter_ranges(inputs, req.parameterRanges)
    sensitivity_parameters = [p for p in req.sensitivityParameters if p in ranges] or list(ranges)[:4]
    horizons = req.timeHorizons or sorted(set([1, 3, inputs.modelYears, 10]))
    evaluations = [_scenario_evaluate(inputs, alt, criteria) for alt in alternatives]
    weighted_ranking = _scenario_rank(evaluations, "decision_score")
    unweighted_ranking = _scenario_rank(evaluations, "unweighted_score")
    recommended_id = weighted_ranking[0]["alternative_id"] if weighted_ranking else ""
    recommended_alt = next((alt for alt, evaluation in zip(alternatives, evaluations) if evaluation["alternative_id"] == recommended_id), alternatives[0] if alternatives else {})
    recommended_eval = next((evaluation for evaluation in evaluations if evaluation["alternative_id"] == recommended_id), evaluations[0] if evaluations else {})

    one_way = _scenario_one_way(inputs, recommended_alt, criteria, ranges, sensitivity_parameters, req.gridPoints)
    multi = _scenario_multi_variable(inputs, recommended_alt, criteria, ranges, sensitivity_parameters) if req.includeMultiVariable else {"parameters": [], "grid": [], "disabled": True}
    threshold = _scenario_threshold(inputs, recommended_alt, criteria, ranges, req.thresholdTarget, req.gridPoints)

    uncertainty = []
    for alt, base in zip(alternatives, evaluations):
        low_overrides = {key: spec["min"] for key, spec in ranges.items()}
        high_overrides = {key: spec["max"] for key, spec in ranges.items()}
        low = _scenario_evaluate(inputs, alt, criteria, low_overrides)
        high = _scenario_evaluate(inputs, alt, criteria, high_overrides)
        scores = [low["decision_score"], base["decision_score"], high["decision_score"]]
        uncertainty.append({"alternative_id": base["alternative_id"], "label": base["label"], "screening_low": min(scores), "base": base["decision_score"], "screening_high": max(scores), "spread": round(max(scores)-min(scores), 2), "interpretation": "Combined range endpoints; not a probability interval."})

    time_horizon = _scenario_time_horizons(inputs, recommended_alt, criteria, horizons)
    scenario_studio = {
        "schema": SCENARIO_STUDIO_SCHEMA,
        "studio_version": APP_VERSION,
        "analysis_mode": mode,
        "alternative_count": len(evaluations),
        "criteria": criteria,
        "parameter_ranges": ranges,
        "alternatives": evaluations,
        "weighted_ranking": weighted_ranking,
        "unweighted_ranking": unweighted_ranking,
        "recommended_alternative_id": recommended_id,
        "recommended_alternative": recommended_eval,
        "dominance_analysis": _scenario_dominance(evaluations),
        "one_way_sensitivity": one_way,
        "multi_variable_sensitivity": multi,
        "threshold_analysis": threshold,
        "uncertainty_envelopes": uncertainty,
        "time_horizon_comparison": time_horizon,
        "stakeholder_distribution": [{"alternative_id": item["alternative_id"], **item["stakeholder_distribution"]} for item in evaluations],
        "reversibility_option_value": [{"alternative_id": item["alternative_id"], "label": item["label"], "reversibility": item["metrics"]["reversibility"], "option_value": item["metrics"]["option_value"]} for item in evaluations],
        "chart_data": {
            "alternative_scores": [{"label": item["label"], "weighted": item["decision_score"], "unweighted": item["unweighted_score"]} for item in evaluations],
            "sensitivity_series": one_way.get("parameters", []),
            "time_horizon_series": time_horizon,
        },
        "workbench_handoff": {
            "required_for": ["probabilistic simulation", "optimization", "engineering models", "domain forecasting", "large sensitivity grids"],
            "recommended_tools": ["economics-forecasting-and-scenario-tool", "graph-studio-parameter-sensitivity", "risk-resilience-impact-matrix", "systems-modeling-tool"],
        },
        "notes": req.notes,
        "warnings": scenario_studio_template()["warnings"],
    }
    packet_out = decision_packet_template()
    packet_out.update(packet)
    packet_out["scenario_studio"] = scenario_studio
    packet_out["sensitivity_analysis"] = one_way
    packet_out["threshold_analysis"] = threshold
    packet_out["uncertainty_analysis"] = {"envelopes": uncertainty, "multi_variable": multi}
    packet_out["scenario_comparison"] = generate_scenario_comparison(ScenarioComparisonRequest(inputs=inputs, packet=packet_out, scenarios=[{"label": item["label"], **item["metrics"]} for item in evaluations])).get("scenario_comparison", {})
    return {"ok": True, "version": APP_VERSION, "schema": SCENARIO_STUDIO_SCHEMA, "scenario_studio": scenario_studio, "decision_packet": packet_out}


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
            "inputs", "results", "decision_packet", "audit", "readiness", "scenario_comparison", "scenario_studio",
            "workbench_handoff", "integrated_brief", "governance", "collaboration", "decision_pack", "publication_studio", "outcome_monitoring"
        ],
        "exports": [
            {"id": "packet_json", "label": "Decision Packet JSON", "description": "Complete normalized packet with module sections and raw artifact snapshots where included."},
            {"id": "integrated_brief_markdown", "label": "Integrated Brief Markdown", "description": "Reviewable decision memo for editing or publication workflow."},
            {"id": "integrated_brief_html", "label": "Integrated Brief HTML", "description": "HTML version suitable for browser print or PDF save flow."},
            {"id": "audit_json", "label": "Audit & Provenance JSON", "description": "Module ledger, source ledger, assumptions, calculation trace, claim trace, and change log."},
            {"id": "readiness_json", "label": "Readiness JSON", "description": "Section readiness, review states, unresolved issues, and export gates."},
            {"id": "scenario_json", "label": "Scenario Comparison JSON", "description": "Compatibility scenario matrix, deltas, rankings, and recommended option."},
            {"id": "scenario_studio_json", "label": "Advanced Scenario Studio JSON", "description": "Alternatives, weighted criteria, sensitivity, thresholds, uncertainty, stakeholder distribution, time horizons, and option value."},
            {"id": "handoff_json", "label": "Workbench Handoff JSON", "description": "Recommended Workbench tools, reasons, priorities, shortcodes, and payload summary."},
            {"id": "governance_json", "label": "Decision Governance JSON", "description": "Decision state, owner, reviewers, conditions, exceptions, conflicts, sign-offs, export gates, and immutable review history."},
            {"id": "collaboration_json", "label": "Collaborative Decision Room JSON", "description": "Private room members, comments, change requests, snapshots, comparisons, notifications, share grants, locks, and activity history."},
            {"id": "decision_pack_json", "label": "Institutional Decision Pack JSON", "description": "Applied domain methodology, required evidence, criteria, indicators, Workbench models, governance roles, readiness rules, and briefing templates."},
            {"id": "publication_json", "label": "Decision Publication JSON", "description": "Structured governed publication, section visibility, citations, redaction, and handoff manifest."},
            {"id": "publication_markdown", "label": "Decision Publication Markdown", "description": "Editable publication with evidence anchors and Harvard bibliography."},
            {"id": "publication_html", "label": "Print-ready Publication HTML", "description": "Browser-printable publication suitable for controlled PDF save workflow."},
            {"id": "bibliography_json", "label": "Bibliography JSON", "description": "Citation registry and evidence-anchor metadata."},
            {"id": "redaction_json", "label": "Redaction Report JSON", "description": "Visibility decisions and deterministic redaction events."},
            {"id": "publication_handoff_json", "label": "Publication Handoffs JSON", "description": "Draft handoffs to Knowledge Library, Research, Publications, and Channel."},
            {"id": "outcome_monitoring_json", "label": "Outcome Monitoring JSON", "description": "Commitments, targets, observations, milestones, risks, assumptions, triggers, and monitoring status."},
            {"id": "decision_registry_json", "label": "Decision Registry JSON", "description": "Durable lifecycle record for the approved, implemented, amended, reassessed, or retired decision."},
            {"id": "reassessment_history_json", "label": "Reassessment History JSON", "description": "Human-owned reassessment events, findings, recommendations, and lifecycle changes."},
            {"id": "public_dossier_json", "label": "Public-safe Decision Dossier JSON", "description": "Governance-gated packet projection with private fields removed."},
            {"id": "readiness_embed_json", "label": "Readiness Embed Descriptor", "description": "Script-free readiness summary for host-controlled rendering."},
            {"id": "scenario_embed_json", "label": "Scenario Embed Descriptor", "description": "Script-free scenario comparison for host-controlled rendering."},
            {"id": "institutional_archive_json", "label": "Institutional Archive JSON", "description": "Bulk packet archive with machine-readable methodology and provenance."},
            {"id": "signed_manifest_json", "label": "Signed Export Manifest", "description": "SHA-256 or HMAC-SHA-256 manifest covering every exported resource."},
            {"id": "platform_core_gateway_json", "label": "Platform Core Gateway Record", "description": "Entities, Evidence Ledger records, provenance links, and exchange manifest."},
            {"id": "internal_events_json", "label": "Internal Event Records", "description": "Hash-addressed webhook-style internal event records."},
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
    scenario_studio = req.scenarioStudio or packet.get("scenario_studio") or generate_scenario_studio(ScenarioStudioRequest(inputs=req.inputs, packet=packet)).get("scenario_studio", {})
    packet["scenario_studio"] = scenario_studio
    workbench_handoff = req.workbenchHandoff or generate_workbench_handoff(WorkbenchHandoffRequest(inputs=req.inputs, results=results, packet=packet, readiness=readiness, scenarioComparison=scenario_comparison)).get("workbench_handoff", {})
    audit = req.audit or generate_audit_provenance(AuditProvenanceRequest(inputs=req.inputs, results=results, packet=packet, reviewStatus=req.status)).get("audit", {})
    integrated = req.integratedBrief or generate_integrated_brief(IntegratedBriefRequest(inputs=req.inputs, results=results, packet=packet, audit=audit)).get("brief", {})
    packet["decision_packet_id"] = packet_id
    governance = packet.get("governance_center", governance_template())
    governance_state = governance.get("current_state", req.status) if isinstance(governance, dict) else req.status
    saved_status = governance_state if req.status == "draft" and governance_state != "draft" else req.status
    collaboration = req.collaboration or packet.get("collaboration_room") or collaborative_room_template()
    packet["collaboration_room"] = collaboration
    decision_pack = req.decisionPack or packet.get("institutional_decision_pack") or {}
    packet["institutional_decision_pack"] = decision_pack
    publication_studio = req.publicationStudio or packet.get("publication_studio") or {}
    packet["publication_studio"] = publication_studio
    outcome_monitoring = req.outcomeMonitoring or packet.get("outcome_monitoring") or outcome_monitoring_template()
    packet["outcome_monitoring"] = outcome_monitoring
    institutional_integration = req.institutionalIntegration or packet.get("institutional_integration") or integration_template(app_version=APP_VERSION, packet_schema=DECISION_PACKET_SCHEMA)
    packet["institutional_integration"] = institutional_integration
    packet["saved_packet"] = {"status": saved_status, "storage": "wordpress_canonical_or_client_fallback", "notes": req.notes}
    saved = {
        "packet_version": APP_VERSION,
        "decision_packet_id": packet_id,
        "title": project_name,
        "project_name": project_name,
        "decision_question": decision_question,
        "status": saved_status,
        "inputs": req.inputs.model_dump(),
        "results": results,
        "decision_packet": packet,
        "audit": audit,
        "readiness": readiness,
        "scenario_comparison": scenario_comparison,
        "scenario_studio": scenario_studio,
        "workbench_handoff": workbench_handoff,
        "integrated_brief": integrated,
        "governance": packet.get("governance_center", governance_template()),
        "collaboration": collaboration,
        "decision_pack": decision_pack,
        "publication_studio": publication_studio,
        "outcome_monitoring": outcome_monitoring,
        "institutional_integration": institutional_integration,
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
    scenario_studio = req.scenarioStudio or packet.get("scenario_studio") or generate_scenario_studio(ScenarioStudioRequest(inputs=inputs, packet=packet)).get("scenario_studio", {})
    packet["scenario_studio"] = scenario_studio
    workbench_handoff = req.workbenchHandoff or generate_workbench_handoff(WorkbenchHandoffRequest(inputs=inputs, results=results, packet=packet, readiness=readiness, scenarioComparison=scenario_comparison)).get("workbench_handoff", {})
    governance = req.governance or packet.get("governance_center") or governance_template()
    packet["governance_center"] = governance
    collaboration = req.collaboration or packet.get("collaboration_room") or collaborative_room_template()
    packet["collaboration_room"] = collaboration
    decision_pack = req.decisionPack or packet.get("institutional_decision_pack") or {}
    packet["institutional_decision_pack"] = decision_pack
    publication_studio = req.publicationStudio or packet.get("publication_studio") or {}
    packet["publication_studio"] = publication_studio
    outcome_monitoring = req.outcomeMonitoring or packet.get("outcome_monitoring") or outcome_monitoring_template()
    packet["outcome_monitoring"] = outcome_monitoring
    institutional_integration = req.institutionalIntegration or packet.get("institutional_integration") or integration_template(app_version=APP_VERSION, packet_schema=DECISION_PACKET_SCHEMA)
    packet["institutional_integration"] = institutional_integration
    audience = str(req.exportAudience or "internal").strip().lower()
    gate = governance.get("export_gate", {}) if isinstance(governance, dict) else {}
    if audience == "reviewed" and not gate.get("reviewed_export_allowed", False):
        return {"ok": False, "version": APP_VERSION, "error": "governance_export_blocked", "export_audience": audience, "governance_export_gate": gate, "message": "Reviewed export is blocked by the current decision-governance state."}
    if audience == "public" and not gate.get("public_export_allowed", False):
        return {"ok": False, "version": APP_VERSION, "error": "governance_export_blocked", "export_audience": audience, "governance_export_gate": gate, "message": "Public export is blocked by the current decision-governance state."}
    brief_payload = req.integratedBrief or generate_integrated_brief(IntegratedBriefRequest(inputs=inputs, results=results, packet=packet, audit=audit))
    brief = brief_payload.get("brief", brief_payload) if isinstance(brief_payload, dict) else {}
    markdown = integrated_brief_markdown(brief) if brief else "# Integrated Decision Brief\n\nNo brief generated."
    html = integrated_brief_html(brief) if brief else "<h1>Integrated Decision Brief</h1><p>No brief generated.</p>"
    bundle = {
        "bundle_version": APP_VERSION,
        "label": req.exportLabel,
        "export_audience": audience,
        "release_classification": "internal_draft" if audience == "internal" and not gate.get("reviewed_export_allowed", False) else audience,
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
            "scenario_studio_json": scenario_studio,
            "workbench_handoff_json": workbench_handoff,
            "governance_json": governance,
            "collaboration_json": collaboration,
            "room_activity_json": collaboration.get("activity_timeline", []) if isinstance(collaboration, dict) else [],
            "snapshot_comparison_json": collaboration.get("snapshot_comparisons", []) if isinstance(collaboration, dict) else [],
            "decision_pack_json": decision_pack,
            "publication_studio_json": publication_studio,
            "publication_markdown": publication_studio.get("markdown", "") if isinstance(publication_studio, dict) else "",
            "publication_html": publication_studio.get("html", "") if isinstance(publication_studio, dict) else "",
            "bibliography_json": publication_studio.get("bibliography", []) if isinstance(publication_studio, dict) else [],
            "redaction_json": publication_studio.get("redaction", {}) if isinstance(publication_studio, dict) else {},
            "publication_handoff_json": publication_studio.get("publication_handoffs", []) if isinstance(publication_studio, dict) else [],
            "outcome_monitoring_json": outcome_monitoring,
            "decision_registry_json": outcome_monitoring.get("decision_registry_entry", packet.get("decision_registry_entry", {})) if isinstance(outcome_monitoring, dict) else {},
            "reassessment_history_json": outcome_monitoring.get("reassessment_history", packet.get("reassessment_history", [])) if isinstance(outcome_monitoring, dict) else [],
            "institutional_integration_json": institutional_integration,
            "public_dossier_json": packet.get("public_dossier", {}),
            "embed_descriptors_json": packet.get("embed_descriptors", []),
            "institutional_archives_json": packet.get("institutional_archives", []),
            "platform_core_gateway_json": packet.get("platform_core_gateway", {}),
            "internal_events_json": packet.get("internal_events", []),
            "sdk_contracts_json": packet.get("sdk_contracts", {}),
        },
        "export_manifest": export_center_template()["exports"],
        "warnings": export_center_template()["warnings"],
        "governance_export_gate": governance.get("export_gate", {}),
    }
    manifest_records = []
    for export_id, export_value in bundle["exports"].items():
        manifest_records.append({"export_id": export_id, "content_hash": _canonical_hash(export_value)})
    bundle["signed_export_manifest"] = sign_manifest({
        "schema": INSTITUTIONAL_ARCHIVE_SCHEMA,
        "bundle_version": APP_VERSION,
        "decision_packet_id": bundle["decision_packet_id"],
        "export_audience": audience,
        "exports": manifest_records,
        "created_at": _utc_now(),
    })
    bundle["exports"]["signed_manifest_json"] = bundle["signed_export_manifest"]
    if not req.includeRawArtifacts:
        bundle["exports"]["decision_packet_json"].pop("module_artifacts_raw", None)
    return {"ok": True, "version": APP_VERSION, "export_bundle": bundle, "export_center": export_center_template()}


def public_landing_template() -> Dict[str, Any]:
    """Professional public-facing product-page structure for Decision Studio v1.15.0."""
    return {
        "page_version": APP_VERSION,
        "headline": "Decision Studio",
        "positioning": "The governance and synthesis layer of the Sustainable Catalyst platform. Decision Studio receives typed evidence, research routes, live indicators, calculations, experiments, entities, and provenance records, then assembles them into a reviewable Decision Packet.",
        "primary_shortcode": "[sc_decision_studio mode=\"full\" title=\"Sustainable Catalyst Decision Studio\"]",
        "landing_shortcode": "[sc_decision_studio mode=\"landing\" title=\"Sustainable Catalyst Decision Studio\"]",
        "demo_shortcode": "[sc_decision_studio mode=\"demo\" title=\"Sustainable Catalyst Decision Studio Demo\"]",
        "workflow": [
            {"step": "Source", "module": "Knowledge Library", "output": "Sources, quotations, Harvard-style citations, bibliographies, and collection context"},
            {"step": "Route", "module": "Research Librarian", "output": "Research routes, recommended titles, evidence gaps, and follow-up questions"},
            {"step": "Observe", "module": "Site Intelligence", "output": "Indicators, country dossiers, live observations, source health, freshness, and methodology"},
            {"step": "Calculate", "module": "Workbench", "output": "Formulas, models, graphs, assumptions, validation checks, and technical reports"},
            {"step": "Test", "module": "Research Lab", "output": "Experiments, notebooks, datasets, instruments, validation results, and limitations"},
            {"step": "Connect", "module": "Platform Core", "output": "Shared entities, Evidence Ledger records, provenance links, relationships, and signed manifests"},
            {"step": "Decide", "module": "Decision Studio", "output": "Alternatives, readiness gates, integrated briefs, audit history, and export bundles"},
        ],
        "sections": [
            "Typed platform artifact contracts",
            "Unified evidence registry",
            "Integrity verification",
            "Decision Packet workspace",
            "Batch and legacy import",
            "Brief readiness and review status",
            "Institutional and domain decision packs",
            "Advanced scenario, sensitivity, threshold, and Workbench handoff",
            "Decision briefing and publication studio",
            "Outcomes, monitoring, reassessment, and Decision Registry",
            "Public API, embeddable readiness and scenario summaries, institutional archives, and Platform Core exchange",
            "Saved packets and export center",
        ],
        "schemas": {
            "artifact": PLATFORM_ARTIFACT_SCHEMA,
            "evidence": EVIDENCE_RECORD_SCHEMA,
            "decision_packet": DECISION_PACKET_SCHEMA,
            "decision_pack": DECISION_PACK_SCHEMA,
            "decision_pack_application": DECISION_PACK_APPLICATION_SCHEMA,
        },
        "boundaries": [
            "Educational and decision-support oriented; not professional advice.",
            "No ESG, SDG, assurance, compliance, engineering, legal, medical, financial, tax, or investment certification.",
            "AI may assist drafting and interpretation; deterministic calculations, assumptions, integrity checks, provenance, and human review remain visible.",
        ],
    }

def public_demo_template() -> Dict[str, Any]:
    """Professional demo-page structure for landing pages and platform demos."""
    return {
        "demo_version": APP_VERSION,
        "headline": "Decision Studio Demo",
        "recommended_demo_flow": [
            "Select an institutional or domain Decision Pack and inspect its evidence, criteria, review, and readiness requirements.",
            "Load the Knowledge Library sample artifact and validate its typed envelope.",
            "Inspect the normalized evidence, citation, provenance, and integrity records.",
            "Import additional Site Intelligence, Workbench, Research Lab, Research Librarian, or Platform Core artifacts.",
            "Run the scorecard, readiness review, advanced scenario analysis, sensitivity ranges, and threshold search.",
            "Generate Workbench handoff recommendations.",
            "Save the Decision Packet locally or export a complete bundle.",
        ],
        "demo_cards": [
            {"title": "Institutional Decision Packs", "description": "Apply reusable climate, infrastructure, urban, procurement, responsible AI, research, environmental, humanitarian, policy, or advisory methodologies.", "shortcode": "[sc_decision_studio mode=\"packs\"]"},
            {"title": "Unified Platform Handoffs", "description": "Show how six current Sustainable Catalyst products feed a typed Decision Packet.", "shortcode": "[sc_decision_studio mode=\"workflow\"]"},
            {"title": "Readiness Review", "description": "Check whether the packet is complete enough for a draft brief or export.", "shortcode": "[sc_decision_studio mode=\"readiness\"]"},
            {"title": "Advanced Scenario Studio", "description": "Compare any number of alternatives, vary assumptions, find thresholds, and inspect stakeholder and time-horizon tradeoffs.", "shortcode": "[sc_decision_studio mode=\"scenario\"]"},
            {"title": "Publication Studio", "description": "Generate citation-native governed decision publications with visibility, redaction, and handoff controls.", "shortcode": "[sc_decision_studio mode=\"publication\"]"},
            {"title": "Export Center", "description": "Generate JSON, Markdown, HTML, audit, readiness, advanced scenario, governance, publication, and handoff exports.", "shortcode": "[sc_decision_studio mode=\"export\"]"},
        ],
        "public_copy": "Use Knowledge Library to source. Research Librarian to route. Site Intelligence to observe. Workbench to calculate. Research Lab to test. Platform Core to connect. Decision Studio to decide.",
    }


def publication_studio_template() -> Dict[str, Any]:
    publication_types = [
        {"id": "executive_decision_memo", "label": "Executive Decision Memo", "audiences": ["internal", "reviewed"], "sections": ["executive_summary", "decision_question", "recommendation", "key_evidence", "tradeoffs", "governance", "next_actions"]},
        {"id": "technical_decision_report", "label": "Technical Decision Report", "audiences": ["internal", "reviewed"], "sections": ["executive_summary", "decision_question", "methodology", "evidence", "scenario_analysis", "technical_analysis", "assumptions", "risks", "governance", "implementation", "monitoring", "bibliography"]},
        {"id": "board_leadership_brief", "label": "Board or Leadership Brief", "audiences": ["reviewed"], "sections": ["executive_summary", "recommendation", "alternatives", "material_risks", "financial_tradeoffs", "governance", "decision_required"]},
        {"id": "alternatives_analysis", "label": "Alternatives Analysis", "audiences": ["internal", "reviewed", "public"], "sections": ["decision_question", "alternatives", "scenario_analysis", "tradeoffs", "sensitivity", "recommendation", "bibliography"]},
        {"id": "public_decision_dossier", "label": "Public Decision Dossier", "audiences": ["public"], "sections": ["executive_summary", "decision_question", "public_interest", "alternatives", "evidence", "methodology", "risks", "governance", "implementation", "monitoring", "bibliography"]},
        {"id": "evidence_appendix", "label": "Evidence Appendix", "audiences": ["internal", "reviewed", "public"], "sections": ["evidence", "quotations", "site_intelligence", "workbench_outputs", "research_lab_outputs", "bibliography"]},
        {"id": "assumptions_register", "label": "Assumptions Register", "audiences": ["internal", "reviewed"], "sections": ["assumptions", "uncertainties", "sensitivity", "review_actions"]},
        {"id": "methodology_statement", "label": "Methodology Statement", "audiences": ["reviewed", "public"], "sections": ["scope", "methodology", "decision_pack", "calculation_methods", "limitations", "governance", "bibliography"]},
        {"id": "audit_provenance_appendix", "label": "Audit and Provenance Appendix", "audiences": ["internal", "reviewed"], "sections": ["source_ledger", "calculation_trace", "review_history", "collaboration_history", "integrity_checks", "transformation_history"]},
        {"id": "implementation_plan", "label": "Implementation Plan", "audiences": ["internal", "reviewed"], "sections": ["recommendation", "implementation", "owners", "milestones", "risks", "monitoring", "reassessment"]},
        {"id": "dissenting_view", "label": "Minority or Dissenting View", "audiences": ["internal", "reviewed"], "sections": ["decision_question", "majority_position", "dissenting_position", "contested_evidence", "unresolved_assumptions", "review_actions"]},
        {"id": "monitoring_plan", "label": "Post-Decision Monitoring Plan", "audiences": ["internal", "reviewed", "public"], "sections": ["decision_commitments", "indicators", "baselines", "targets", "owners", "monitoring", "reassessment", "public_reporting"]},
    ]
    return {
        "schema": PUBLICATION_STUDIO_SCHEMA,
        "version": APP_VERSION,
        "publication_types": publication_types,
        "citation_styles": ["Harvard"],
        "audiences": {
            "internal": {"governance_gate": "none", "default_visibility": "private"},
            "reviewed": {"governance_gate": "reviewed_export_allowed", "default_visibility": "institutional"},
            "public": {"governance_gate": "public_export_allowed", "default_visibility": "public", "redaction_required": True},
        },
        "publication_targets": [
            {"id": "knowledge_library", "label": "Knowledge Library"},
            {"id": "research", "label": "Research"},
            {"id": "publications", "label": "Publications"},
            {"id": "channel", "label": "Channel"},
        ],
        "boundaries": [
            "Publication templates do not approve, certify, assure, or professionally sign off a decision.",
            "Reviewed and public publication remains controlled by the Decision Governance and Review Center.",
            "Print-ready HTML can be saved as PDF through the browser; generated content must be reviewed before release.",
        ],
    }


def _publication_type(type_id: str) -> Dict[str, Any]:
    normalized = str(type_id or "executive_decision_memo").strip().lower().replace("-", "_")
    aliases = {"executive_memo": "executive_decision_memo", "technical_report": "technical_decision_report", "public_dossier": "public_decision_dossier", "board_brief": "board_leadership_brief"}
    normalized = aliases.get(normalized, normalized)
    for item in publication_studio_template()["publication_types"]:
        if item["id"] == normalized:
            return item
    return publication_studio_template()["publication_types"][0]


def _publication_citations(packet: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    candidates.extend([x for x in _list(packet.get("citations")) if isinstance(x, dict)])
    candidates.extend([x for x in _list(packet.get("evidence_registry")) if isinstance(x, dict)])
    candidates.extend([x for x in _list(packet.get("sources")) if isinstance(x, dict)])
    seen: set[str] = set()
    records: List[Dict[str, Any]] = []
    for item in candidates:
        title = str(item.get("title") or item.get("source_title") or item.get("name") or "Untitled source").strip()
        citation = str(item.get("citation") or "").strip()
        authors = item.get("authors") if isinstance(item.get("authors"), list) else []
        year = str(item.get("published_at") or item.get("year") or item.get("date") or "n.d.")[:4]
        author_text = ", ".join(str(a) for a in authors if a) or str(item.get("author") or item.get("organization") or item.get("source_product") or "Sustainable Catalyst")
        url = str(item.get("source_url") or item.get("url") or "")
        if not citation:
            citation = f"{author_text} ({year}) {title}." + (f" Available at: {url}." if url else "")
        key = (citation or title).lower()
        if key in seen:
            continue
        seen.add(key)
        idx = len(records) + 1
        records.append({
            "citation_id": f"S{idx}", "anchor": f"[S{idx}]", "title": title,
            "authors": authors or [author_text], "year": year, "citation": citation,
            "in_text": f"({author_text.split(',')[0]}, {year})", "url": url,
            "source_type": item.get("source_type", item.get("artifact_type", "source")),
            "confidence": item.get("confidence", "not specified"),
            "artifact_id": item.get("artifact_id", ""),
        })
    return records


def _publication_content(packet: Dict[str, Any], brief: Dict[str, Any], inputs: DecisionInputs, results: Dict[str, Any]) -> Dict[str, Any]:
    governance = packet.get("governance_center", {}) if isinstance(packet.get("governance_center"), dict) else {}
    collaboration = packet.get("collaboration_room", {}) if isinstance(packet.get("collaboration_room"), dict) else {}
    scenario = packet.get("scenario_studio", {}) if isinstance(packet.get("scenario_studio"), dict) else {}
    decision_pack = packet.get("institutional_decision_pack", {}) if isinstance(packet.get("institutional_decision_pack"), dict) else {}
    audit = packet.get("audit_and_provenance", {}) if isinstance(packet.get("audit_and_provenance"), dict) else {}
    return {
        "executive_summary": brief.get("executive_summary") or f"Decision review for {inputs.projectName}.",
        "decision_question": packet.get("project", {}).get("decision_question") or inputs.decisionQuestion,
        "recommendation": brief.get("recommendation_posture") or results.get("status") or "Human review required.",
        "key_evidence": brief.get("evidence_and_source_ledger", {}).get("findings", []),
        "tradeoffs": brief.get("four_pillar_analysis", {}).get("findings", []),
        "governance": {"state": governance.get("current_state", "draft"), "owner": governance.get("decision_owner", {}), "conditions": governance.get("approval_conditions", []), "exceptions": governance.get("exceptions", [])},
        "next_actions": brief.get("next_review_actions", []),
        "methodology": packet.get("methodologies", []) or decision_pack.get("methodology", decision_pack.get("summary", "Decision Studio deterministic synthesis and human review.")),
        "evidence": packet.get("evidence_registry", []) or packet.get("sources", []),
        "scenario_analysis": scenario or packet.get("scenario_comparison", {}),
        "technical_analysis": packet.get("technical_artifacts", []) or packet.get("calculation_trace", []),
        "assumptions": packet.get("assumptions", []),
        "risks": packet.get("risks", []) or brief.get("claim_and_narrative_risk", {}).get("findings", []),
        "implementation": packet.get("execution_and_recovery", {}) or {"status": "Not yet specified"},
        "monitoring": packet.get("monitoring_plan", {}) or {"status": "Monitoring plan requires assignment."},
        "alternatives": scenario.get("alternatives", []) or packet.get("scenarios", {}).get("records", []),
        "material_risks": packet.get("risks", []),
        "financial_tradeoffs": packet.get("financial_tradeoffs", {}) or results.get("finance", {}),
        "decision_required": inputs.decisionQuestion,
        "public_interest": packet.get("public_interest_statement", "Public-interest implications should be reviewed and stated explicitly."),
        "quotations": packet.get("quotations", []),
        "site_intelligence": packet.get("live_evidence", []),
        "workbench_outputs": packet.get("workbench_calculations", []) or packet.get("technical_artifacts", []),
        "research_lab_outputs": packet.get("experimental_evidence", []),
        "uncertainties": packet.get("uncertainty_analysis", {}) or brief.get("assumptions_and_uncertainties", {}).get("findings", []),
        "sensitivity": packet.get("sensitivity_analysis", {}),
        "review_actions": brief.get("next_review_actions", []),
        "scope": packet.get("decision_framing", {}) or packet.get("project", {}),
        "decision_pack": decision_pack,
        "calculation_methods": packet.get("calculation_trace", []),
        "limitations": brief.get("boundaries", []) or ["Decision support only; qualified human review remains required."],
        "source_ledger": audit.get("source_ledger", packet.get("sources", [])),
        "calculation_trace": audit.get("calculation_trace", packet.get("calculation_trace", [])),
        "review_history": governance.get("review_history", []),
        "collaboration_history": collaboration.get("activity_timeline", []),
        "integrity_checks": packet.get("integrity_checks", []),
        "transformation_history": [x.get("provenance", {}).get("transformation_history", []) for x in packet.get("platform_handoffs", []) if isinstance(x, dict)],
        "owners": [governance.get("decision_owner", {})] + [x for x in governance.get("reviewers", []) if isinstance(x, dict)],
        "milestones": packet.get("implementation_milestones", []),
        "reassessment": {"due_at": governance.get("reassessment_due_at", ""), "approval_expires_at": governance.get("approval_expires_at", "")},
        "majority_position": brief.get("recommendation_posture", "Not recorded"),
        "dissenting_position": packet.get("dissenting_view", "No dissenting view recorded."),
        "contested_evidence": packet.get("contested_evidence", []),
        "unresolved_assumptions": [x for x in packet.get("assumptions", []) if isinstance(x, dict) and str(x.get("review_status", "")).lower() not in {"reviewed", "accepted", "closed"}],
        "decision_commitments": packet.get("decision_commitments", []),
        "indicators": packet.get("indicator_plan", []) or packet.get("live_evidence", []),
        "baselines": packet.get("baselines", []),
        "targets": packet.get("targets", []),
        "public_reporting": packet.get("public_reporting_plan", "Publication cadence not yet specified."),
    }


def _publication_text(value: Any) -> str:
    if value in (None, "", [], {}):
        return "Not specified."
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(f"- {_compact_text(item)}" for item in value) or "Not specified."
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def _apply_publication_redaction(sections: List[Dict[str, Any]], audience: str, rules: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    output = json.loads(json.dumps(sections, ensure_ascii=False))
    log: List[Dict[str, Any]] = []
    remove_ids = {str(r.get("section_id", "")) for r in rules if str(r.get("type", "")).lower() == "remove_section"}
    filtered: List[Dict[str, Any]] = []
    for section in output:
        if section.get("id") in remove_ids or (audience == "public" and section.get("visibility") in {"private", "institutional"}):
            log.append({"action": "section_removed", "section_id": section.get("id"), "reason": "rule" if section.get("id") in remove_ids else "public_visibility_gate"})
            continue
        text = str(section.get("content", ""))
        for rule in rules:
            if str(rule.get("type", "")).lower() == "replace_text" and rule.get("term"):
                replacement = str(rule.get("replacement") or "[REDACTED]")
                updated, count = re.subn(re.escape(str(rule["term"])), replacement, text, flags=re.IGNORECASE)
                if count:
                    log.append({"action": "text_replaced", "section_id": section.get("id"), "term": str(rule["term"]), "count": count})
                    text = updated
        if audience == "public":
            text, emails = re.subn(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", "[REDACTED EMAIL]", text, flags=re.IGNORECASE)
            text, phones = re.subn(r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)", "[REDACTED PHONE]", text)
            if emails: log.append({"action": "email_redacted", "section_id": section.get("id"), "count": emails})
            if phones: log.append({"action": "phone_redacted", "section_id": section.get("id"), "count": phones})
        section["content"] = text
        filtered.append(section)
    return filtered, log


def publication_markdown(publication: Dict[str, Any]) -> str:
    lines = [f"# {publication.get('title', 'Decision Publication')}"]
    if publication.get("subtitle"):
        lines += ["", publication["subtitle"]]
    lines += ["", f"**Publication type:** {publication.get('publication_type_label')}", f"**Audience:** {publication.get('audience')}", f"**Decision Packet:** {publication.get('decision_packet_id')}", ""]
    for section in publication.get("sections", []):
        lines += [f"## {section.get('title')}", str(section.get("content") or "Not specified."), ""]
    bibliography = publication.get("bibliography", [])
    if bibliography:
        lines += ["## Bibliography"] + [f"{c.get('anchor')} {c.get('citation')}" for c in bibliography] + [""]
    lines += ["## Publication Boundary", "This publication is a governed decision-support artifact. It is not professional approval, certification, assurance, or regulated advice.", ""]
    return "\n".join(lines)


def publication_html(publication: Dict[str, Any]) -> str:
    def esc(value: Any) -> str:
        return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    body = f"<article class=\"scds-publication\"><header><h1>{esc(publication.get('title', 'Decision Publication'))}</h1>"
    if publication.get("subtitle"):
        body += f"<p>{esc(publication['subtitle'])}</p>"
    body += f"<p><strong>Type:</strong> {esc(publication.get('publication_type_label'))} · <strong>Audience:</strong> {esc(publication.get('audience'))}</p></header>"
    for section in publication.get("sections", []):
        content = esc(section.get("content", "")).replace("\n", "<br>")
        body += f"<section data-section=\"{esc(section.get('id'))}\"><h2>{esc(section.get('title'))}</h2><p>{content}</p></section>"
    if publication.get("bibliography"):
        body += "<section><h2>Bibliography</h2><ol>" + "".join(f"<li id=\"{esc(c.get('citation_id'))}\">{esc(c.get('citation'))}</li>" for c in publication["bibliography"]) + "</ol></section>"
    body += "<footer><p>This publication is a governed decision-support artifact. It is not professional approval, certification, assurance, or regulated advice.</p></footer></article>"
    return body


def _publication_handoffs(publication: Dict[str, Any], targets: List[str]) -> List[Dict[str, Any]]:
    allowed = {x["id"] for x in publication_studio_template()["publication_targets"]}
    selected = [str(x).strip().lower().replace("-", "_") for x in targets] or ["knowledge_library", "publications"]
    return [{
        "schema": PUBLICATION_HANDOFF_SCHEMA,
        "handoff_id": f"pub-{publication.get('publication_id')}-{target}",
        "target": target,
        "status": "draft",
        "publication_id": publication.get("publication_id"),
        "decision_packet_id": publication.get("decision_packet_id"),
        "title": publication.get("title"),
        "publication_type": publication.get("publication_type"),
        "audience": publication.get("audience"),
        "content_hash": publication.get("content_hash"),
        "governance_state": publication.get("governance_state"),
        "review_required": True,
    } for target in selected if target in allowed]


def generate_publication(req: PublicationStudioRequest) -> Dict[str, Any]:
    packet = decision_packet_template()
    packet.update(req.packet or {})
    results = req.results or analyze(req.inputs)
    governance = req.governance or packet.get("governance_center") or governance_template()
    audience = str(req.audience or "internal").strip().lower()
    if audience == "institutional": audience = "reviewed"
    gate = governance.get("export_gate", {}) if isinstance(governance, dict) else {}
    if audience == "reviewed" and not gate.get("reviewed_export_allowed", False):
        return {"ok": False, "version": APP_VERSION, "error": "governance_publication_blocked", "audience": audience, "governance_export_gate": gate, "message": "Reviewed publication is blocked by the current decision-governance state."}
    if audience == "public" and not gate.get("public_export_allowed", False):
        return {"ok": False, "version": APP_VERSION, "error": "governance_publication_blocked", "audience": audience, "governance_export_gate": gate, "message": "Public publication is blocked by the current decision-governance state."}
    brief_payload = req.integratedBrief or generate_integrated_brief(IntegratedBriefRequest(inputs=req.inputs, results=results, packet=packet))
    brief = brief_payload.get("brief", brief_payload) if isinstance(brief_payload, dict) else {}
    type_record = _publication_type(req.publicationType)
    content = _publication_content(packet, brief, req.inputs, results)
    citations = _publication_citations(packet)
    anchors = " ".join(c["anchor"] for c in citations[:3])
    sections: List[Dict[str, Any]] = []
    visibility_map = {str(k): str(v).lower() for k, v in (req.sectionVisibility or {}).items()}
    for section_id in type_record["sections"]:
        if section_id == "dissenting_position" and not req.includeDissentingView:
            continue
        if section_id == "monitoring" and not req.includeMonitoringPlan:
            continue
        visibility = visibility_map.get(section_id, "public" if audience == "public" else ("institutional" if audience == "reviewed" else "private"))
        section_content = _publication_text(content.get(section_id))
        if citations and section_id in {"executive_summary", "key_evidence", "evidence", "methodology", "scenario_analysis", "technical_analysis", "site_intelligence", "workbench_outputs", "research_lab_outputs", "contested_evidence"}:
            section_content = f"{section_content}\n\nEvidence anchors: {anchors}"
        sections.append({"id": section_id, "title": section_id.replace("_", " ").title(), "visibility": visibility, "content": section_content})
    sections, redaction_log = _apply_publication_redaction(sections, audience, req.redactionRules)
    packet_id = packet.get("decision_packet_id") or _safe_packet_id(req.inputs.projectName)
    pub_id = "PUB-" + hashlib.sha256(f"{packet_id}|{type_record['id']}|{req.title}|{len(sections)}".encode()).hexdigest()[:12].upper()
    publication = {
        "schema": PUBLICATION_STUDIO_SCHEMA,
        "publication_id": pub_id,
        "publication_version": APP_VERSION,
        "publication_type": type_record["id"],
        "publication_type_label": type_record["label"],
        "title": req.title or f"{req.inputs.projectName}: {type_record['label']}",
        "subtitle": req.subtitle,
        "audience": audience,
        "prepared_by": req.preparedBy,
        "decision_packet_id": packet_id,
        "governance_state": governance.get("current_state", "draft") if isinstance(governance, dict) else "draft",
        "governance_export_gate": gate,
        "sections": sections,
        "bibliography": citations,
        "citation_style": "Harvard",
        "redaction": {"schema": PUBLICATION_REDACTION_SCHEMA, "required": audience == "public", "rules_applied": len(req.redactionRules), "events": redaction_log, "complete": True},
        "notes": req.notes,
        "warnings": publication_studio_template()["boundaries"],
    }
    publication["content_hash"] = "sha256:" + _canonical_hash({"sections": sections, "bibliography": citations, "audience": audience, "type": type_record["id"]})
    publication["markdown"] = publication_markdown(publication)
    publication["html"] = publication_html(publication)
    publication["publication_handoffs"] = _publication_handoffs(publication, req.publicationTargets)
    packet["decision_packet_schema"] = DECISION_PACKET_SCHEMA
    packet["publication_studio_schema"] = PUBLICATION_STUDIO_SCHEMA
    packet["publication_handoff_schema"] = PUBLICATION_HANDOFF_SCHEMA
    packet["publication_redaction_schema"] = PUBLICATION_REDACTION_SCHEMA
    packet["publication_studio"] = publication
    packet.setdefault("publication_registry", []).append({k: publication[k] for k in ("publication_id", "publication_type", "title", "audience", "content_hash", "governance_state")})
    packet["publication_handoffs"] = publication["publication_handoffs"]
    packet["redaction_log"] = redaction_log
    formats = packet.setdefault("export_center", {}).setdefault("available_formats", [])
    for fmt in ("publication_json", "publication_markdown", "publication_html", "bibliography_json", "redaction_json", "publication_handoff_json"):
        if fmt not in formats: formats.append(fmt)
    return {"ok": True, "version": APP_VERSION, "schema": PUBLICATION_STUDIO_SCHEMA, "publication": publication, "decision_packet": packet, "publication_studio": publication_studio_template()}


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
        "platform_artifact_schema": PLATFORM_ARTIFACT_SCHEMA,
        "evidence_record_schema": EVIDENCE_RECORD_SCHEMA,
        "governance_schema": GOVERNANCE_SCHEMA,
        "review_event_schema": REVIEW_EVENT_SCHEMA,
        "scenario_studio_schema": SCENARIO_STUDIO_SCHEMA,
        "collaboration_room_schema": COLLABORATION_ROOM_SCHEMA,
        "collaboration_event_schema": COLLABORATION_EVENT_SCHEMA,
        "decision_pack_schema": DECISION_PACK_SCHEMA,
        "decision_pack_application_schema": DECISION_PACK_APPLICATION_SCHEMA,
        "publication_studio_schema": PUBLICATION_STUDIO_SCHEMA,
        "publication_handoff_schema": PUBLICATION_HANDOFF_SCHEMA,
        "publication_redaction_schema": PUBLICATION_REDACTION_SCHEMA,
        "outcome_monitoring_schema": OUTCOME_MONITORING_SCHEMA,
        "reassessment_event_schema": REASSESSMENT_EVENT_SCHEMA,
        "decision_registry_schema": DECISION_REGISTRY_SCHEMA,
        "public_api_schema": PUBLIC_API_SCHEMA,
        "embed_descriptor_schema": EMBED_DESCRIPTOR_SCHEMA,
        "institutional_archive_schema": INSTITUTIONAL_ARCHIVE_SCHEMA,
        "webhook_event_schema": WEBHOOK_EVENT_SCHEMA,
        "sdk_contract_schema": SDK_CONTRACT_SCHEMA,
        "platform_core_gateway_schema": PLATFORM_CORE_GATEWAY_SCHEMA,
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

def _institutional_api_scopes(request: Request) -> set[str]:
    supplied = request.headers.get("x-scds-api-key", "").strip()
    super_key = os.getenv("SCDS_API_KEY", "").strip()
    if supplied and super_key and secrets.compare_digest(supplied, super_key):
        return {"*"}
    raw = os.getenv("SCDS_INSTITUTIONAL_API_KEYS", "{}").strip() or "{}"
    try:
        catalog = json.loads(raw)
    except json.JSONDecodeError:
        catalog = {}
    scopes = catalog.get(supplied, []) if supplied and isinstance(catalog, dict) else []
    return {str(scope) for scope in scopes} if isinstance(scopes, list) else set()


def _require_institutional_scope(request: Request, scope: str) -> Optional[JSONResponse]:
    scopes = _institutional_api_scopes(request)
    if "*" in scopes or scope in scopes:
        return None
    return JSONResponse(status_code=403, content={"ok": False, "version": APP_VERSION, "error": "institutional_scope_required", "required_scope": scope})


@app.get("/integrations/adapters")
def integrations_adapters_endpoint():
    return {"ok": True, "version": APP_VERSION, "adapters": artifact_adapter_catalog()}

@app.get("/integrations/platform")
def integrations_platform_endpoint():
    return {"ok": True, "version": APP_VERSION, "schema": PLATFORM_ARTIFACT_SCHEMA, "products": module_integrations(), "contracts": platform_handoff_contracts(), "legacy_modules": legacy_module_integrations()}

@app.get("/integrations/contracts")
def integrations_contracts_endpoint():
    return {"ok": True, "version": APP_VERSION, "artifact_schema": PLATFORM_ARTIFACT_SCHEMA, "evidence_schema": EVIDENCE_RECORD_SCHEMA, "contracts": platform_handoff_contracts()}

@app.get("/integrations/contracts/{product_id}")
def integrations_contract_endpoint(product_id: str):
    contract = platform_contract(product_id)
    if not contract:
        return JSONResponse(status_code=404, content={"ok": False, "version": APP_VERSION, "error": "unknown_platform_product", "product_id": product_id})
    return {"ok": True, "version": APP_VERSION, "artifact_schema": PLATFORM_ARTIFACT_SCHEMA, "contract": contract}

@app.post("/integrations/validate")
def integrations_validate_endpoint(req: TypedArtifactValidationRequest):
    result = validate_typed_artifact(req.artifact, req.sourceProduct, req.strict)
    if not result["ok"]:
        return JSONResponse(status_code=422, content=result)
    return result

@app.post("/integrations/import-batch")
def integrations_import_batch_endpoint(req: ArtifactBatchImportRequest):
    return import_artifact_batch(req.artifacts, packet=req.packet, preserve_raw=req.preserveRaw, strict=req.strict)

@app.get("/decision-packet/platform-handoffs")
def decision_packet_platform_handoffs_endpoint():
    return {"ok": True, "version": APP_VERSION, "artifact_schema": PLATFORM_ARTIFACT_SCHEMA, "evidence_schema": EVIDENCE_RECORD_SCHEMA, "contracts": platform_handoff_contracts(), "decision_packet": decision_packet_template()}

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

@app.get("/governance/states")
def governance_states_endpoint():
    return {"ok": True, "version": APP_VERSION, **governance_state_catalog()}

@app.get("/governance/template")
def governance_template_endpoint():
    return {"ok": True, "version": APP_VERSION, "governance": governance_template(), "state_catalog": governance_state_catalog()}

@app.post("/governance/evaluate")
def governance_evaluate_endpoint(req: GovernanceRequest):
    return evaluate_governance(req)

@app.post("/governance/transition")
def governance_transition_endpoint(req: GovernanceRequest):
    return evaluate_governance(req)

@app.post("/decision-packet/governance")
def decision_packet_governance_endpoint(req: GovernanceRequest):
    return evaluate_governance(req)

@app.post("/governance/history/verify")
def governance_history_verify_endpoint(req: GovernanceRequest):
    return {"ok": True, "version": APP_VERSION, "integrity": verify_review_history(req.reviewHistory)}

@app.get("/decision-packs/catalog")
def decision_packs_catalog_endpoint():
    packs = institutional_decision_pack_catalog()
    return {"ok": True, "version": APP_VERSION, "schema": DECISION_PACK_SCHEMA, "packs": packs, "count": len(packs)}

@app.get("/decision-packs/{pack_id}")
def decision_pack_endpoint(pack_id: str):
    pack = institutional_decision_pack(pack_id)
    if not pack:
        return JSONResponse(status_code=404, content={"ok": False, "version": APP_VERSION, "error": "unknown_decision_pack", "pack_id": pack_id})
    return {"ok": True, "version": APP_VERSION, "schema": DECISION_PACK_SCHEMA, "pack": pack}

@app.post("/decision-packs/validate")
def decision_pack_validate_endpoint(req: DecisionPackRequest):
    result = validate_institutional_decision_pack(req)
    if not result.get("ok"):
        return JSONResponse(status_code=404, content=result)
    return result

@app.post("/decision-packs/apply")
def decision_pack_apply_endpoint(req: DecisionPackRequest):
    result = apply_institutional_decision_pack(req)
    if not result.get("ok"):
        return JSONResponse(status_code=404, content=result)
    return result

@app.post("/decision-packet/domain-pack")
def decision_packet_domain_pack_endpoint(req: DecisionPackRequest):
    result = apply_institutional_decision_pack(req)
    if not result.get("ok"):
        return JSONResponse(status_code=404, content=result)
    return result

@app.get("/collaboration/roles")
def collaboration_roles_endpoint():
    return {"ok": True, "version": APP_VERSION, **collaboration_role_catalog()}

@app.get("/collaboration/template")
def collaboration_template_endpoint():
    return {"ok": True, "version": APP_VERSION, "room": collaborative_room_template(), "roles": collaboration_role_catalog(), "decision_packet": decision_packet_template()}

@app.post("/collaboration/room")
def collaboration_room_endpoint(req: CollaborativeRoomRequest):
    result = generate_collaborative_room(req)
    if not result.get("ok", False):
        return JSONResponse(status_code=403 if result.get("error") == "collaboration_permission_denied" else 409, content=result)
    return result

@app.post("/collaboration/action")
def collaboration_action_endpoint(req: CollaborativeRoomRequest):
    result = generate_collaborative_room(req)
    if not result.get("ok", False):
        return JSONResponse(status_code=403 if result.get("error") == "collaboration_permission_denied" else 409, content=result)
    return result

@app.post("/collaboration/comment")
def collaboration_comment_endpoint(req: CollaborativeRoomRequest):
    result = generate_collaborative_room(req.model_copy(update={"action": "add_comment"}))
    if not result.get("ok", False): return JSONResponse(status_code=403 if result.get("error") == "collaboration_permission_denied" else 409, content=result)
    return result

@app.post("/collaboration/change-request")
def collaboration_change_request_endpoint(req: CollaborativeRoomRequest):
    result = generate_collaborative_room(req.model_copy(update={"action": "create_change_request"}))
    if not result.get("ok", False): return JSONResponse(status_code=403 if result.get("error") == "collaboration_permission_denied" else 409, content=result)
    return result

@app.post("/collaboration/snapshot")
def collaboration_snapshot_endpoint(req: CollaborativeRoomRequest):
    result = generate_collaborative_room(req.model_copy(update={"action": "snapshot"}))
    if not result.get("ok", False): return JSONResponse(status_code=403 if result.get("error") == "collaboration_permission_denied" else 409, content=result)
    return result

@app.post("/collaboration/share")
def collaboration_share_endpoint(req: CollaborativeRoomRequest):
    result = generate_collaborative_room(req.model_copy(update={"action": "invite_member"}))
    if not result.get("ok", False): return JSONResponse(status_code=403 if result.get("error") == "collaboration_permission_denied" else 409, content=result)
    return result

@app.post("/collaboration/contact-handoff")
def collaboration_contact_handoff_endpoint(req: CollaborativeRoomRequest):
    result = generate_collaborative_room(req.model_copy(update={"action": "contact_handoff"}))
    if not result.get("ok", False): return JSONResponse(status_code=403 if result.get("error") == "collaboration_permission_denied" else 409, content=result)
    return result

@app.post("/decision-packet/collaboration")
def decision_packet_collaboration_endpoint(req: CollaborativeRoomRequest):
    result = generate_collaborative_room(req)
    if not result.get("ok", False): return JSONResponse(status_code=403 if result.get("error") == "collaboration_permission_denied" else 409, content=result)
    return result

@app.get("/publication-studio/template")
def publication_studio_template_endpoint():
    return {"ok": True, "version": APP_VERSION, "publication_studio": publication_studio_template()}

@app.post("/publication-studio/generate")
def publication_studio_generate_endpoint(req: PublicationStudioRequest):
    result = generate_publication(req)
    if not result.get("ok", False):
        return JSONResponse(status_code=409, content=result)
    return result

@app.post("/publication-studio/redact")
def publication_studio_redact_endpoint(req: PublicationStudioRequest):
    result = generate_publication(req)
    if not result.get("ok", False):
        return JSONResponse(status_code=409, content=result)
    return result

@app.post("/publication-studio/handoff")
def publication_studio_handoff_endpoint(req: PublicationStudioRequest):
    result = generate_publication(req)
    if not result.get("ok", False):
        return JSONResponse(status_code=409, content=result)
    return {"ok": True, "version": APP_VERSION, "schema": PUBLICATION_HANDOFF_SCHEMA, "publication": result["publication"], "publication_handoffs": result["publication"].get("publication_handoffs", []), "decision_packet": result["decision_packet"]}

@app.post("/decision-packet/publication")
def decision_packet_publication_endpoint(req: PublicationStudioRequest):
    result = generate_publication(req)
    if not result.get("ok", False):
        return JSONResponse(status_code=409, content=result)
    return result


def _run_outcome_monitoring(req: OutcomeMonitoringRequest, action: str):
    return generate_outcome_monitoring(
        req.model_copy(update={"action": action}),
        packet_template_factory=decision_packet_template,
        governance_template_factory=governance_template,
        app_version=APP_VERSION,
        packet_schema=DECISION_PACKET_SCHEMA,
        canonical_hash=_canonical_hash,
        utc_now=_utc_now,
    )


@app.get("/outcomes/template")
def outcomes_template_endpoint():
    return {"ok": True, "version": APP_VERSION, "outcome_monitoring": outcome_monitoring_template()}


@app.post("/outcomes/evaluate")
def outcomes_evaluate_endpoint(req: OutcomeMonitoringRequest):
    return _run_outcome_monitoring(req, "evaluate")


@app.post("/outcomes/record-observation")
def outcomes_record_observation_endpoint(req: OutcomeMonitoringRequest):
    result = _run_outcome_monitoring(req, "record_observation")
    if not result.get("ok", False):
        return JSONResponse(status_code=422, content=result)
    return result


@app.post("/outcomes/reassess")
def outcomes_reassess_endpoint(req: OutcomeMonitoringRequest):
    result = _run_outcome_monitoring(req, "reassess")
    if not result.get("ok", False):
        return JSONResponse(status_code=422, content=result)
    return result


@app.post("/outcomes/amend")
def outcomes_amend_endpoint(req: OutcomeMonitoringRequest):
    result = _run_outcome_monitoring(req, "amend")
    if not result.get("ok", False):
        return JSONResponse(status_code=422, content=result)
    return result


@app.post("/outcomes/retire")
def outcomes_retire_endpoint(req: OutcomeMonitoringRequest):
    result = _run_outcome_monitoring(req, "retire")
    if not result.get("ok", False):
        return JSONResponse(status_code=422, content=result)
    return result


@app.post("/decision-packet/outcomes")
def decision_packet_outcomes_endpoint(req: OutcomeMonitoringRequest):
    return _run_outcome_monitoring(req, req.action or "evaluate")


@app.get("/api/v1/capabilities")
def public_api_capabilities_endpoint():
    return {"ok": True, "version": APP_VERSION, "integration": integration_template(app_version=APP_VERSION, packet_schema=DECISION_PACKET_SCHEMA)}


@app.get("/api/v1/sdk/contracts")
def public_api_sdk_contracts_endpoint():
    return sdk_contracts(app_version=APP_VERSION, packet_schema=DECISION_PACKET_SCHEMA)


@app.post("/api/v1/public-dossier")
def public_api_dossier_endpoint(req: PublicIntegrationRequest):
    result = public_dossier(req.packet, app_version=APP_VERSION, packet_schema=DECISION_PACKET_SCHEMA, include_provenance=req.includeProvenance, include_methodology=req.includeMethodology)
    if not result.get("ok"):
        return JSONResponse(status_code=409, content=result)
    return result


@app.post("/api/v1/embeds/readiness")
def public_api_readiness_embed_endpoint(req: PublicIntegrationRequest):
    return readiness_embed(req.packet, app_version=APP_VERSION)


@app.post("/api/v1/embeds/scenario")
def public_api_scenario_embed_endpoint(req: PublicIntegrationRequest):
    return scenario_embed(req.packet, app_version=APP_VERSION)


@app.post("/api/v1/packets/export")
def institutional_bulk_export_endpoint(req: PublicIntegrationRequest, request: Request):
    denied = _require_institutional_scope(request, "packet:read")
    if denied: return denied
    return institutional_archive(req.packets or ([req.packet] if req.packet else []), app_version=APP_VERSION, packet_schema=DECISION_PACKET_SCHEMA, label=req.archiveLabel, public_only=False)


@app.post("/api/v1/packets/import")
def institutional_bulk_import_endpoint(req: PublicIntegrationRequest, request: Request):
    denied = _require_institutional_scope(request, "packet:write")
    if denied: return denied
    archive = req.payload.get("archive") if isinstance(req.payload.get("archive"), dict) else req.payload
    result = import_archive(archive, app_version=APP_VERSION, packet_schema=DECISION_PACKET_SCHEMA)
    if not result.get("ok"):
        return JSONResponse(status_code=422, content=result)
    return result


@app.post("/api/v1/archive")
def institutional_archive_endpoint(req: PublicIntegrationRequest, request: Request):
    denied = _require_institutional_scope(request, "archive:write")
    if denied: return denied
    return institutional_archive(req.packets or ([req.packet] if req.packet else []), app_version=APP_VERSION, packet_schema=DECISION_PACKET_SCHEMA, label=req.archiveLabel, public_only=req.audience == "public")


@app.post("/api/v1/platform-core/gateway")
def platform_core_gateway_endpoint(req: PublicIntegrationRequest, request: Request):
    denied = _require_institutional_scope(request, "gateway:write")
    if denied: return denied
    return platform_core_gateway(req.packet, req.payload, app_version=APP_VERSION, packet_schema=DECISION_PACKET_SCHEMA)


@app.post("/api/v1/events")
def institutional_event_endpoint(req: PublicIntegrationRequest, request: Request):
    denied = _require_institutional_scope(request, "event:emit")
    if denied: return denied
    return webhook_event(req.eventType, req.payload, app_version=APP_VERSION, actor=req.actor, target=req.target)


@app.post("/decision-packet/institutional-integration")
def decision_packet_institutional_integration_endpoint(req: PublicIntegrationRequest):
    packet = decision_packet_template()
    packet.update(req.packet or {})
    packet["packet_version"] = APP_VERSION
    packet["decision_packet_schema"] = DECISION_PACKET_SCHEMA
    packet["institutional_integration"] = integration_template(app_version=APP_VERSION, packet_schema=DECISION_PACKET_SCHEMA)
    packet["sdk_contracts"] = sdk_contracts(app_version=APP_VERSION, packet_schema=DECISION_PACKET_SCHEMA)
    packet["embed_descriptors"] = [readiness_embed(packet, app_version=APP_VERSION)["embed"], scenario_embed(packet, app_version=APP_VERSION)["embed"]]
    if governance_public_allowed(packet):
        packet["public_dossier"] = public_dossier(packet, app_version=APP_VERSION, packet_schema=DECISION_PACKET_SCHEMA).get("public_dossier", {})
    return {"ok": True, "version": APP_VERSION, "decision_packet": packet, "institutional_integration": packet["institutional_integration"]}


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

@app.get("/scenario-studio/template")
def scenario_studio_template_endpoint():
    return {"ok": True, "version": APP_VERSION, "template": scenario_studio_template()}

@app.post("/scenario-studio/analyze")
def scenario_studio_analyze_endpoint(req: ScenarioStudioRequest):
    return generate_scenario_studio(req, "full")

@app.post("/scenario-studio/sensitivity")
def scenario_studio_sensitivity_endpoint(req: ScenarioStudioRequest):
    result = generate_scenario_studio(req, "sensitivity")
    return {"ok": True, "version": APP_VERSION, "schema": SCENARIO_STUDIO_SCHEMA, "sensitivity_analysis": result["scenario_studio"]["one_way_sensitivity"], "multi_variable_sensitivity": result["scenario_studio"]["multi_variable_sensitivity"], "scenario_studio": result["scenario_studio"], "decision_packet": result["decision_packet"]}

@app.post("/scenario-studio/threshold")
def scenario_studio_threshold_endpoint(req: ScenarioStudioRequest):
    result = generate_scenario_studio(req, "threshold")
    return {"ok": True, "version": APP_VERSION, "schema": SCENARIO_STUDIO_SCHEMA, "threshold_analysis": result["scenario_studio"]["threshold_analysis"], "scenario_studio": result["scenario_studio"], "decision_packet": result["decision_packet"]}

@app.post("/decision-packet/scenario-studio")
def decision_packet_scenario_studio_endpoint(req: ScenarioStudioRequest):
    return generate_scenario_studio(req, "packet")

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
    result = generate_export_bundle(req)
    if not result.get("ok", False):
        return JSONResponse(status_code=409, content=result)
    return result

@app.post("/decision-packet/export-bundle")
def decision_packet_export_bundle_endpoint(req: ExportBundleRequest):
    result = generate_export_bundle(req)
    if not result.get("ok", False):
        return JSONResponse(status_code=409, content=result)
    return result


@app.get("/public/landing-template")
def public_landing_template_endpoint():
    return {"ok": True, "version": APP_VERSION, "landing": public_landing_template()}

@app.get("/public/demo-template")
def public_demo_template_endpoint():
    return {"ok": True, "version": APP_VERSION, "demo": public_demo_template()}


@app.get("/templates")
def templates():
    return {"scenario_templates": ["Baseline", "Conservative", "Expected", "Ambitious", "Stress test"], "shortcodes": ["[sc_decision_studio mode=\"full\"]", "[sc_decision_studio mode=\"risk\"]", "[sc_decision_studio mode=\"report\"]"], "ai_endpoints": ["/release", "/ai/status", "/brief", "/report", "/integrated-brief", "/decision-packet/brief", "/brief-readiness", "/decision-packet/readiness", "/review/status", "/scenario-comparison", "/decision-packet/scenario-comparison", "/scenario-studio/template", "/scenario-studio/analyze", "/scenario-studio/sensitivity", "/scenario-studio/threshold", "/decision-packet/scenario-studio", "/workbench/handoff", "/decision-packet/workbench-handoff", "/decision-packet/storage-template", "/decision-packet/save-template", "/export-center/template", "/export-center/bundle", "/decision-packet/export-bundle", "/public/landing-template", "/public/demo-template", "/governance/states", "/governance/template", "/governance/evaluate", "/governance/transition", "/decision-packet/governance", "/governance/history/verify", "/collaboration/roles", "/collaboration/template", "/collaboration/room", "/collaboration/action", "/collaboration/comment", "/collaboration/change-request", "/collaboration/snapshot", "/collaboration/share", "/collaboration/contact-handoff", "/decision-packet/collaboration", "/decision-packs/catalog", "/decision-packs/{pack_id}", "/decision-packs/validate", "/decision-packs/apply", "/decision-packet/domain-pack", "/publication-studio/template", "/publication-studio/generate", "/publication-studio/redact", "/publication-studio/handoff", "/decision-packet/publication", "/outcomes/template", "/outcomes/evaluate", "/outcomes/record-observation", "/outcomes/reassess", "/outcomes/amend", "/outcomes/retire", "/decision-packet/outcomes", "/api/v1/capabilities", "/api/v1/sdk/contracts", "/api/v1/public-dossier", "/api/v1/embeds/readiness", "/api/v1/embeds/scenario", "/api/v1/packets/export", "/api/v1/packets/import", "/api/v1/archive", "/api/v1/platform-core/gateway", "/api/v1/events", "/decision-packet/institutional-integration"], "integration_endpoints": ["/release", "/integrations/platform", "/integrations/contracts", "/integrations/validate", "/integrations/import-batch", "/decision-packet/platform-handoffs", "/integrations/modules", "/decision-packet/template", "/decision-packet/analyze", "/audit/template", "/audit/generate", "/review/status-template", "/brief-readiness", "/decision-packet/readiness", "/integrations/adapters", "/integrations/import", "/integrations/import-batch", "/decision-packet/import", "/integrated-brief", "/decision-packet/brief", "/brief-readiness", "/decision-packet/readiness", "/review/status", "/scenario-comparison", "/decision-packet/scenario-comparison", "/scenario-studio/template", "/scenario-studio/analyze", "/scenario-studio/sensitivity", "/scenario-studio/threshold", "/decision-packet/scenario-studio", "/workbench/handoff", "/decision-packet/workbench-handoff", "/decision-packet/storage-template", "/decision-packet/save-template", "/export-center/template", "/export-center/bundle", "/decision-packet/export-bundle", "/public/landing-template", "/public/demo-template", "/governance/states", "/governance/template", "/governance/evaluate", "/governance/transition", "/decision-packet/governance", "/governance/history/verify", "/collaboration/roles", "/collaboration/template", "/collaboration/room", "/collaboration/action", "/collaboration/comment", "/collaboration/change-request", "/collaboration/snapshot", "/collaboration/share", "/collaboration/contact-handoff", "/decision-packet/collaboration", "/decision-packs/catalog", "/decision-packs/{pack_id}", "/decision-packs/validate", "/decision-packs/apply", "/decision-packet/domain-pack", "/publication-studio/template", "/publication-studio/generate", "/publication-studio/redact", "/publication-studio/handoff", "/decision-packet/publication", "/outcomes/template", "/outcomes/evaluate", "/outcomes/record-observation", "/outcomes/reassess", "/outcomes/amend", "/outcomes/retire", "/decision-packet/outcomes", "/api/v1/capabilities", "/api/v1/sdk/contracts", "/api/v1/public-dossier", "/api/v1/embeds/readiness", "/api/v1/embeds/scenario", "/api/v1/packets/export", "/api/v1/packets/import", "/api/v1/archive", "/api/v1/platform-core/gateway", "/api/v1/events", "/decision-packet/institutional-integration"]}
