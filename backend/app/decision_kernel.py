from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List
from pydantic import BaseModel, Field

DECISION_KERNEL_SCHEMA = "scds-decision-kernel/1.0"
DECISION_MODULE_CONTRACT_SCHEMA = "scds-decision-module-contract/1.0"
DECISION_MODULE_REGISTRY_SCHEMA = "scds-decision-module-registry/1.0"
KERNEL_VERSION = "1.0"

KERNEL_OBJECTS: List[str] = [
    "decision",
    "alternative",
    "criterion",
    "evidence_ref",
    "assumption",
    "scenario",
    "recommendation",
    "review",
    "challenge",
    "outcome",
    "artifact_ref",
    "provenance_ref",
]

KERNEL_AUTHORITIES: Dict[str, str] = {
    "decision_identity": "decision-studio-kernel",
    "decision_lifecycle": "decision-studio-kernel",
    "module_registration": "decision-studio-kernel",
    "evidence_identity_and_provenance": "platform-core",
    "calculation_execution": "workbench",
    "research_experiment_execution": "research-lab",
    "dataset_and_notebook_execution": "workspace",
    "live_context_observation": "site-intelligence",
    "final_decision_authority": "human-governed",
}

MODULE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "canvas": {
        "module_id": "canvas",
        "display_name": "Canvas",
        "domain": "general-decision-architecture",
        "purpose": "General structured decision framing, comparison, review, and outcome architecture.",
        "module_contract_schema": DECISION_MODULE_CONTRACT_SCHEMA,
        "kernel_contract_schema": DECISION_KERNEL_SCHEMA,
        "status": "foundation",
        "extends_kernel_objects": ["decision", "alternative", "criterion", "evidence_ref", "assumption", "scenario", "recommendation", "review", "outcome"],
        "capabilities": [
            "decision-framing", "objectives-and-constraints", "stakeholder-mapping",
            "criteria-and-alternatives", "evidence-and-assumptions", "scenario-structure",
            "tradeoff-analysis", "recommendation-review", "outcome-recording",
        ],
        "providers": {
            "evidence": ["knowledge-library", "research-librarian"],
            "compute": ["workbench", "workspace", "research-lab"],
            "context": ["site-intelligence"],
        },
        "boundaries": [
            "does-not-own-shared-decision-identity",
            "does-not-auto-select-a-winner",
            "does-not-bypass-human-review",
        ],
    },
    "finance": {
        "module_id": "finance",
        "display_name": "Finance",
        "domain": "financial-and-economic-decision-analysis",
        "purpose": "Financial assumptions, cash-flow, valuation, cost-benefit, capital, and financial-risk decision context.",
        "module_contract_schema": DECISION_MODULE_CONTRACT_SCHEMA,
        "kernel_contract_schema": DECISION_KERNEL_SCHEMA,
        "status": "foundation",
        "extends_kernel_objects": ["decision", "alternative", "criterion", "assumption", "scenario", "artifact_ref", "provenance_ref", "recommendation"],
        "capabilities": [
            "financial-assumptions", "cash-flow-model-reference", "valuation-reference",
            "cost-and-revenue-objects", "capital-and-discounting", "financial-risk",
            "financial-scenarios", "financial-sensitivity", "cost-benefit-analysis",
        ],
        "providers": {
            "compute_authority": "workbench",
            "datasets": ["workspace", "knowledge-library"],
            "research": ["research-librarian", "research-lab"],
        },
        "boundaries": [
            "decision-studio-does-not-duplicate-workbench-calculation-runtime",
            "model-output-is-not-automatic-recommendation",
            "financial-score-is-not-final-decision-authority",
        ],
    },
    "narrative-risk": {
        "module_id": "narrative-risk",
        "display_name": "Narrative Risk",
        "domain": "qualitative-narrative-and-emerging-risk-analysis",
        "purpose": "Claims, risk drivers, signals, actors, exposures, impacts, scenarios, mitigations, and competing narratives.",
        "module_contract_schema": DECISION_MODULE_CONTRACT_SCHEMA,
        "kernel_contract_schema": DECISION_KERNEL_SCHEMA,
        "status": "foundation",
        "extends_kernel_objects": ["decision", "evidence_ref", "assumption", "scenario", "challenge", "artifact_ref", "provenance_ref", "outcome"],
        "capabilities": [
            "risk-narratives", "risk-claims", "risk-drivers-and-signals", "risk-events-and-actors",
            "exposure-and-impact", "likelihood-context", "risk-scenarios", "mitigations",
            "competing-narratives", "contradiction-tracing",
        ],
        "providers": {
            "evidence": ["knowledge-library", "research-librarian"],
            "graphs": ["platform-core"],
            "context": ["site-intelligence"],
        },
        "boundaries": [
            "narrative-is-not-treated-as-fact-without-evidence",
            "risk-likelihood-must-preserve-uncertainty",
            "does-not-auto-escalate-or-execute-actions",
        ],
    },
    "global-impact": {
        "module_id": "global-impact",
        "display_name": "Global Impact Catalyst",
        "domain": "sustainability-global-impact-and-development-analysis",
        "purpose": "Environmental, social, economic, carbon, resource, SDG, geographic, and distributional impact decision context.",
        "module_contract_schema": DECISION_MODULE_CONTRACT_SCHEMA,
        "kernel_contract_schema": DECISION_KERNEL_SCHEMA,
        "status": "foundation",
        "extends_kernel_objects": ["decision", "alternative", "criterion", "evidence_ref", "assumption", "scenario", "artifact_ref", "provenance_ref", "outcome"],
        "capabilities": [
            "impact-objectives", "indicators-and-targets", "impact-boundaries", "impact-stakeholders",
            "impact-pathways", "environmental-impact", "social-impact", "economic-impact",
            "sdg-alignment", "carbon-impact", "resource-impact", "distributional-impact", "impact-scenarios",
        ],
        "providers": {
            "evidence": ["knowledge-library", "research-librarian"],
            "compute": ["workbench", "workspace", "research-lab"],
            "spatial_and_live_context": ["site-intelligence"],
        },
        "boundaries": [
            "sdg-alignment-is-not-proof-of-impact",
            "modeled-impact-is-not-observed-outcome",
            "distributional-judgments-remain-explicit-and-reviewable",
        ],
    },
}


class DecisionKernelRequest(BaseModel):
    kernel: Dict[str, Any] = Field(default_factory=dict)
    strict: bool = True


class ModuleContractRequest(BaseModel):
    contract: Dict[str, Any] = Field(default_factory=dict)
    strict: bool = True


def module_registry() -> Dict[str, Any]:
    return {
        "schema": DECISION_MODULE_REGISTRY_SCHEMA,
        "kernel_schema": DECISION_KERNEL_SCHEMA,
        "module_contract_schema": DECISION_MODULE_CONTRACT_SCHEMA,
        "module_count": len(MODULE_REGISTRY),
        "modules": [deepcopy(MODULE_REGISTRY[k]) for k in sorted(MODULE_REGISTRY)],
    }


def module_contract(module_id: str) -> Dict[str, Any] | None:
    item = MODULE_REGISTRY.get(str(module_id or "").strip().lower())
    return deepcopy(item) if item else None


def kernel_contracts() -> Dict[str, Any]:
    return {
        "decision_kernel_schema": DECISION_KERNEL_SCHEMA,
        "decision_module_contract_schema": DECISION_MODULE_CONTRACT_SCHEMA,
        "decision_module_registry_schema": DECISION_MODULE_REGISTRY_SCHEMA,
        "kernel_version": KERNEL_VERSION,
        "kernel_objects": list(KERNEL_OBJECTS),
        "authorities": deepcopy(KERNEL_AUTHORITIES),
        "principles": {
            "kernel_owns_shared_decision_identity": True,
            "modules_extend_kernel_objects_not_fork_them": True,
            "module_outputs_are_provenance_bearing_artifacts": True,
            "cross_module_evidence_references_are_shared": True,
            "compute_runtime_is_delegated_to_domain_runtimes": True,
            "ai_or_model_output_is_not_final_decision_authority": True,
            "final_decision_authority_is_human_governed": True,
        },
    }


def decision_kernel_template() -> Dict[str, Any]:
    return {
        "schema": DECISION_KERNEL_SCHEMA,
        "kernel_version": KERNEL_VERSION,
        "decision": {
            "decision_id": "",
            "decision_question": "",
            "title": "",
            "status": "draft",
        },
        "module_bindings": [
            {
                "module_id": "canvas",
                "module_contract_schema": DECISION_MODULE_CONTRACT_SCHEMA,
                "enabled": True,
                "configuration": {},
            }
        ],
        "shared_objects": {name: [] for name in KERNEL_OBJECTS if name != "decision"},
        "authorities": deepcopy(KERNEL_AUTHORITIES),
        "provenance": {
            "created_by": "",
            "created_at": "",
            "source_artifacts": [],
        },
    }


def _module_ids(bindings: Any) -> List[str]:
    out: List[str] = []
    if not isinstance(bindings, list):
        return out
    for item in bindings:
        if isinstance(item, str):
            mid = item.strip().lower()
        elif isinstance(item, dict):
            mid = str(item.get("module_id", "")).strip().lower()
        else:
            mid = ""
        if mid:
            out.append(mid)
    return out


def validate_decision_kernel(payload: Dict[str, Any], strict: bool = True) -> Dict[str, Any]:
    data = deepcopy(payload or {})
    errors: List[str] = []
    warnings: List[str] = []

    if data.get("schema") not in {None, "", DECISION_KERNEL_SCHEMA}:
        errors.append("unsupported_kernel_schema")
    decision = data.get("decision") if isinstance(data.get("decision"), dict) else {}
    if not str(decision.get("decision_id", "")).strip():
        errors.append("decision_id_required")
    if not str(decision.get("decision_question", "")).strip():
        errors.append("decision_question_required")

    bindings = data.get("module_bindings", [])
    mids = _module_ids(bindings)
    if not mids:
        errors.append("at_least_one_module_binding_required")
    unknown = sorted({m for m in mids if m not in MODULE_REGISTRY})
    if unknown:
        errors.append("unknown_module_binding:" + ",".join(unknown))
    if len(mids) != len(set(mids)):
        errors.append("duplicate_module_binding")
    if "canvas" not in mids:
        warnings.append("canvas_not_enabled_general_decision_framing_must_be_supplied_elsewhere")

    supplied_authorities = data.get("authorities", {}) if isinstance(data.get("authorities"), dict) else {}
    final_authority = supplied_authorities.get("final_decision_authority", KERNEL_AUTHORITIES["final_decision_authority"])
    if final_authority != "human-governed":
        errors.append("final_decision_authority_must_remain_human_governed")

    normalized = decision_kernel_template()
    normalized["decision"].update(decision)
    normalized["module_bindings"] = []
    for mid in mids:
        if mid not in MODULE_REGISTRY:
            continue
        source = next((b for b in bindings if isinstance(b, dict) and str(b.get("module_id", "")).strip().lower() == mid), {})
        normalized["module_bindings"].append({
            "module_id": mid,
            "module_contract_schema": DECISION_MODULE_CONTRACT_SCHEMA,
            "enabled": bool(source.get("enabled", True)) if isinstance(source, dict) else True,
            "configuration": deepcopy(source.get("configuration", {})) if isinstance(source, dict) and isinstance(source.get("configuration", {}), dict) else {},
        })
    if isinstance(data.get("shared_objects"), dict):
        for key in normalized["shared_objects"]:
            if isinstance(data["shared_objects"].get(key), list):
                normalized["shared_objects"][key] = deepcopy(data["shared_objects"][key])
    if isinstance(data.get("provenance"), dict):
        normalized["provenance"].update(deepcopy(data["provenance"]))

    if strict and warnings:
        pass
    return {
        "ok": not errors,
        "schema": DECISION_KERNEL_SCHEMA,
        "errors": errors,
        "warnings": warnings,
        "module_ids": mids,
        "normalized_kernel": normalized,
    }


def validate_module_contract(module_id: str, payload: Dict[str, Any], strict: bool = True) -> Dict[str, Any]:
    mid = str(module_id or "").strip().lower()
    expected = module_contract(mid)
    if not expected:
        return {"ok": False, "module_id": mid, "errors": ["unknown_module"], "warnings": []}
    data = deepcopy(payload or {})
    errors: List[str] = []
    warnings: List[str] = []
    if data.get("module_id") not in {None, "", mid}:
        errors.append("module_id_mismatch")
    if data.get("module_contract_schema") not in {None, "", DECISION_MODULE_CONTRACT_SCHEMA}:
        errors.append("unsupported_module_contract_schema")
    if data.get("kernel_contract_schema") not in {None, "", DECISION_KERNEL_SCHEMA}:
        errors.append("unsupported_kernel_contract_schema")
    requested = data.get("extends_kernel_objects")
    if isinstance(requested, list):
        invalid = sorted({str(x) for x in requested if str(x) not in KERNEL_OBJECTS})
        if invalid:
            errors.append("unknown_kernel_object:" + ",".join(invalid))
    elif requested is not None:
        errors.append("extends_kernel_objects_must_be_array")
    if strict and data.get("final_decision_authority") not in {None, "", "human-governed"}:
        errors.append("module_cannot_override_final_decision_authority")
    if not data:
        warnings.append("empty_contract_validated_against_registered_foundation")
    return {
        "ok": not errors,
        "module_id": mid,
        "errors": errors,
        "warnings": warnings,
        "registered_contract": expected,
    }
