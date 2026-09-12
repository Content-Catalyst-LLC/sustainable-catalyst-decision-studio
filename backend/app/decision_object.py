from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List

from pydantic import BaseModel, Field

DECISION_OBJECT_SCHEMA = "scds-decision-object/1.0"
PLATFORM_CONTEXT_SCHEMA = "scds-platform-context/1.0"
DECISION_OBJECT_MIGRATION_SCHEMA = "scds-decision-object-migration/1.0"


class DecisionObjectRequest(BaseModel):
    packet: Dict[str, Any] = Field(default_factory=dict)
    decisionObject: Dict[str, Any] = Field(default_factory=dict)
    platformArtifacts: List[Dict[str, Any]] = Field(default_factory=list)
    includeEmpty: bool = True


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _deep_get(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    return value


def _first(data: Dict[str, Any], paths: List[str], default: Any = "") -> Any:
    for path in paths:
        value = _deep_get(data, path, None)
        if value not in (None, "", [], {}):
            return value
    return default


def _records(data: Dict[str, Any], paths: List[str]) -> List[Any]:
    for path in paths:
        value = _deep_get(data, path, None)
        if isinstance(value, list) and value:
            return deepcopy(value)
    return []


def _fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def platform_context_catalog() -> List[Dict[str, Any]]:
    return [
        {
            "id": "knowledge-library",
            "name": "Knowledge Library",
            "role": "evidence",
            "provides": ["sources", "citations", "evidence_records", "source_bundles", "evidence_quality"],
            "decision_object_targets": ["evidence", "provenance", "assumptions"],
        },
        {
            "id": "research-librarian",
            "name": "Research Librarian",
            "role": "research_routing",
            "provides": ["research_routes", "source_discovery", "evidence_gaps", "contradictions", "follow_up_questions"],
            "decision_object_targets": ["evidence", "uncertainties", "counterarguments", "provenance"],
        },
        {
            "id": "site-intelligence",
            "name": "Site Intelligence",
            "role": "real_world_context",
            "provides": ["observations", "geospatial_context", "environmental_signals", "country_context", "monitoring_signals"],
            "decision_object_targets": ["context", "evidence", "scenarios", "outcome_review"],
        },
        {
            "id": "workbench",
            "name": "Workbench",
            "role": "computation",
            "provides": ["calculations", "engineering_models", "simulations", "optimization", "reports"],
            "decision_object_targets": ["models", "scenarios", "tradeoffs", "uncertainties", "provenance"],
        },
        {
            "id": "research-lab",
            "name": "Research Lab",
            "role": "analysis",
            "provides": ["experiments", "statistical_models", "causal_inference", "bayesian_analysis", "sensitivity_analysis"],
            "decision_object_targets": ["models", "evidence", "scenarios", "uncertainties", "confidence"],
        },
        {
            "id": "platform-core",
            "name": "Platform Core",
            "role": "infrastructure",
            "provides": ["durable_objects", "provenance", "storage", "processing_adapters", "cross_product_identity"],
            "decision_object_targets": ["identity", "provenance", "platform_context", "links"],
        },
        {
            "id": "decision-studio",
            "name": "Decision Studio",
            "role": "choice",
            "provides": ["framing", "alternatives", "criteria", "tradeoffs", "recommendation", "governance", "decision_record"],
            "decision_object_targets": ["question", "objective", "alternatives", "criteria", "recommendation", "decision", "outcome_review"],
        },
    ]


def platform_context_template(app_version: str, packet_schema: str) -> Dict[str, Any]:
    return {
        "schema": PLATFORM_CONTEXT_SCHEMA,
        "version": app_version,
        "decision_packet_schema": packet_schema,
        "generated_at": _utc_now(),
        "products": platform_context_catalog(),
        "artifact_links": [],
        "context_summary": {
            "products_available": len(platform_context_catalog()),
            "products_with_artifacts": 0,
            "artifact_count": 0,
            "roles": ["evidence", "research_routing", "real_world_context", "computation", "analysis", "infrastructure", "choice"],
        },
        "boundary": "Platform context describes provenance-aware handoffs. It does not claim that external products accepted, verified, or approved an artifact unless that status is explicitly recorded by the source product.",
    }


def decision_object_template(app_version: str, packet_schema: str) -> Dict[str, Any]:
    return {
        "schema": DECISION_OBJECT_SCHEMA,
        "version": app_version,
        "decision_id": "",
        "status": "draft",
        "created_at": "",
        "updated_at": "",
        "question": "",
        "objective": "",
        "alternatives": [],
        "criteria": [],
        "constraints": [],
        "assumptions": [],
        "evidence": [],
        "evidence_bundles": [],
        "source_bundles": [],
        "models": [],
        "scenarios": [],
        "uncertainties": [],
        "stakeholders": [],
        "tradeoffs": [],
        "tradeoff_matrices": [],
        "recommendation": {},
        "confidence": {},
        "counterarguments": [],
        "provenance": {
            "source_packet_schema": packet_schema,
            "source_packet_id": "",
            "source_packet_fingerprint": "",
            "migration_schema": DECISION_OBJECT_MIGRATION_SCHEMA,
            "records": [],
        },
        "decision": {},
        "rationale": [],
        "outcome_review": {},
        "platform_context": platform_context_template(app_version, packet_schema),
        "links": [],
        "compatibility": {
            "decision_packet_projection": True,
            "packet_schema_breaking_changes": False,
            "lossless_source_packet_reference": True,
        },
    }


def decision_object_from_packet(packet: Dict[str, Any], app_version: str, packet_schema: str) -> Dict[str, Any]:
    packet = deepcopy(packet or {})
    out = decision_object_template(app_version, packet_schema)
    project = _dict(packet.get("project"))
    framing = _dict(packet.get("decision_framing"))
    governance = _dict(packet.get("governance_center"))
    registry = _dict(packet.get("decision_registry_entry"))
    outcome = _dict(packet.get("outcome_monitoring"))
    brief = _dict(packet.get("integrated_decision_brief"))
    comparison = _dict(packet.get("scenario_comparison"))
    studio = _dict(packet.get("scenario_studio"))

    decision_id = str(packet.get("decision_packet_id") or registry.get("decision_id") or "")
    question = str(_first(packet, ["decision_framing.decision_question", "project.decision_question", "decision_question"], ""))
    objective = _first(packet, ["decision_framing.objective", "project.objective", "integrated_decision_brief.objective", "decision_framing.goal"], "")
    constraints = _first(packet, ["decision_framing.constraints", "constraints"], [])
    if isinstance(constraints, str):
        constraints = [constraints] if constraints.strip() else []
    alternatives = _records(packet, ["scenario_studio.alternatives", "scenario_comparison.matrix", "scenarios.records", "alternatives"])
    scenarios = _records(packet, ["scenario_studio.alternatives", "scenarios.records", "scenario_comparison.scenarios"])
    criteria = _records(packet, ["criteria_registry", "institutional_decision_pack.criteria", "criteria"])
    assumptions = _records(packet, ["assumptions", "scenario_studio.assumptions", "integrated_decision_brief.assumptions"])
    evidence = _records(packet, ["evidence_registry", "evidence_and_measurement.records", "sources", "evidence_ledger"])
    models = _records(packet, ["technical_artifacts", "workbench_handoffs", "model_plan", "experimental_evidence"])
    uncertainties = _records(packet, ["uncertainty_analysis.records", "risks", "evidence_gaps", "claim_and_risk_review.records"])
    stakeholders = _records(packet, ["stakeholders", "stakeholder_analysis.records", "institutional_decision_pack.stakeholders"])
    tradeoffs = _records(packet, ["tradeoffs", "financial_tradeoffs.records", "scenario_comparison.tradeoffs"])
    if not tradeoffs and packet.get("financial_tradeoffs"):
        tradeoffs = [deepcopy(packet.get("financial_tradeoffs"))]
    counterarguments = _records(packet, ["counterarguments", "claim_and_risk_review.records", "governance_center.exceptions"])
    rationale = _records(packet, ["rationale", "integrated_decision_brief.rationale", "decision_registry_entry.rationale"])
    if not rationale:
        summary = brief.get("executive_summary") or brief.get("summary")
        rationale = [summary] if summary else []

    recommendation = _first(packet, ["integrated_decision_brief.recommendation", "scenario_comparison.recommendation", "recommendation"], {})
    if isinstance(recommendation, str):
        recommendation = {"summary": recommendation}
    confidence = _first(packet, ["confidence", "integrated_decision_brief.confidence", "scenario_comparison.confidence"], {})
    if isinstance(confidence, (int, float, str)):
        confidence = {"value": confidence}

    decision_record = {}
    if registry:
        decision_record = {
            "status": registry.get("status") or governance.get("current_state") or packet.get("status", "draft"),
            "decision": registry.get("decision") or registry.get("selected_alternative") or "",
            "decided_at": registry.get("decided_at") or registry.get("approved_at") or "",
            "owner": governance.get("owner") or registry.get("owner") or "",
        }
    elif governance:
        decision_record = {"status": governance.get("current_state", "draft"), "owner": governance.get("owner", "")}

    out.update({
        "decision_id": decision_id,
        "status": str(packet.get("status") or governance.get("current_state") or registry.get("status") or "draft"),
        "created_at": str(packet.get("created_at") or packet.get("saved_packet", {}).get("saved_at") or ""),
        "updated_at": _utc_now(),
        "question": question,
        "objective": objective,
        "alternatives": alternatives,
        "criteria": criteria,
        "constraints": deepcopy(constraints),
        "assumptions": assumptions,
        "evidence": evidence,
        "models": models,
        "scenarios": scenarios,
        "uncertainties": uncertainties,
        "stakeholders": stakeholders,
        "tradeoffs": tradeoffs,
        "recommendation": deepcopy(recommendation),
        "confidence": deepcopy(confidence),
        "counterarguments": counterarguments,
        "decision": decision_record,
        "rationale": rationale,
        "outcome_review": deepcopy(outcome),
    })
    out["provenance"] = {
        "source_packet_schema": str(packet.get("decision_packet_schema") or packet.get("packet_schema") or packet_schema),
        "source_packet_id": decision_id,
        "source_packet_fingerprint": _fingerprint(packet),
        "migration_schema": DECISION_OBJECT_MIGRATION_SCHEMA,
        "records": deepcopy(_records(packet, ["provenance_links", "audit_trail", "audit_and_provenance.events"])),
    }
    out["source_packet"] = packet
    out["mapping_summary"] = decision_object_completeness(out)
    return out


def normalize_decision_object(decision_object: Dict[str, Any], packet: Dict[str, Any], app_version: str, packet_schema: str) -> Dict[str, Any]:
    base = decision_object_from_packet(packet, app_version, packet_schema) if packet else decision_object_template(app_version, packet_schema)
    supplied = deepcopy(decision_object or {})
    for key, value in supplied.items():
        if key in {"schema", "version"}:
            continue
        base[key] = value
    base["schema"] = DECISION_OBJECT_SCHEMA
    base["version"] = app_version
    base["updated_at"] = _utc_now()
    base["mapping_summary"] = decision_object_completeness(base)
    return base


def attach_platform_context(decision_object: Dict[str, Any], artifacts: List[Dict[str, Any]], app_version: str, packet_schema: str) -> Dict[str, Any]:
    out = normalize_decision_object(decision_object, {}, app_version, packet_schema)
    context = platform_context_template(app_version, packet_schema)
    catalog = {item["id"]: item for item in context["products"]}
    links: List[Dict[str, Any]] = []
    products = set()
    for index, artifact in enumerate(artifacts or []):
        if not isinstance(artifact, dict):
            continue
        product_id = str(artifact.get("product_id") or artifact.get("source_product") or artifact.get("source") or "unknown").strip().lower().replace(" ", "-")
        product = catalog.get(product_id)
        if product:
            products.add(product_id)
        links.append({
            "link_id": str(artifact.get("artifact_id") or artifact.get("id") or f"artifact-{index+1}"),
            "product_id": product_id,
            "product_name": product["name"] if product else str(artifact.get("product_name") or product_id),
            "role": product["role"] if product else "external_context",
            "artifact_schema": str(artifact.get("schema") or artifact.get("artifact_schema") or ""),
            "artifact_type": str(artifact.get("artifact_type") or artifact.get("type") or "artifact"),
            "provenance": deepcopy(artifact.get("provenance") or {}),
            "status": str(artifact.get("status") or "linked"),
            "payload_fingerprint": _fingerprint(artifact.get("payload") if "payload" in artifact else artifact),
        })
    context["artifact_links"] = links
    context["context_summary"] = {
        **context["context_summary"],
        "products_with_artifacts": len(products),
        "artifact_count": len(links),
        "coverage_percent": round((len(products) / max(1, len(catalog))) * 100, 1),
    }
    out["platform_context"] = context
    out["links"] = deepcopy(links)
    out["mapping_summary"] = decision_object_completeness(out)
    return out


def decision_object_completeness(obj: Dict[str, Any]) -> Dict[str, Any]:
    required = ["question", "alternatives", "criteria", "evidence", "assumptions", "recommendation", "provenance"]
    present: List[str] = []
    missing: List[str] = []
    for key in required:
        value = obj.get(key)
        if value not in (None, "", [], {}):
            present.append(key)
        else:
            missing.append(key)
    return {
        "required_fields": required,
        "present": present,
        "missing": missing,
        "completeness_percent": round((len(present) / len(required)) * 100, 1),
        "review_ready": not missing,
    }


def decision_object_to_packet(decision_object: Dict[str, Any], app_version: str, packet_schema: str) -> Dict[str, Any]:
    obj = normalize_decision_object(decision_object, {}, app_version, packet_schema)
    source = deepcopy(_dict(obj.get("source_packet")))
    packet = source if source else {
        "packet_version": app_version,
        "decision_packet_schema": packet_schema,
        "decision_packet_id": obj.get("decision_id") or "",
        "status": obj.get("status") or "draft",
        "project": {},
        "decision_framing": {},
    }
    packet["packet_version"] = app_version
    packet["decision_packet_schema"] = packet_schema
    packet["decision_packet_id"] = obj.get("decision_id") or packet.get("decision_packet_id", "")
    packet["status"] = obj.get("status") or packet.get("status", "draft")
    packet.setdefault("project", {})["decision_question"] = obj.get("question", "")
    packet.setdefault("decision_framing", {})["decision_question"] = obj.get("question", "")
    packet["decision_framing"]["objective"] = obj.get("objective", "")
    packet["decision_framing"]["constraints"] = deepcopy(obj.get("constraints", []))
    packet["criteria_registry"] = deepcopy(obj.get("criteria", []))
    packet["assumptions"] = deepcopy(obj.get("assumptions", []))
    packet["evidence_registry"] = deepcopy(obj.get("evidence", []))
    packet["evidence_bundles"] = deepcopy(obj.get("evidence_bundles", []))
    packet["source_bundles"] = deepcopy(obj.get("source_bundles", []))
    packet.setdefault("scenarios", {})["records"] = deepcopy(obj.get("scenarios") or obj.get("alternatives", []))
    packet["technical_artifacts"] = deepcopy(obj.get("models", []))
    packet["risks"] = deepcopy(obj.get("uncertainties", []))
    packet["decision_object"] = {key: deepcopy(value) for key, value in obj.items() if key != "source_packet"}
    packet.setdefault("audit_trail", []).append({
        "at": _utc_now(),
        "action": "decision_object_projected_to_packet",
        "by": "decision-studio",
        "version": app_version,
        "schema": DECISION_OBJECT_SCHEMA,
    })
    return packet
