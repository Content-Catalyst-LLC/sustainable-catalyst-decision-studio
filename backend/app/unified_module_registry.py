from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import BaseModel, Field

from app.decision_kernel import (
    DECISION_KERNEL_SCHEMA,
    DECISION_MODULE_CONTRACT_SCHEMA,
    DECISION_MODULE_REGISTRY_SCHEMA,
    module_contract,
    module_registry,
)
from app.domains.canvas import CANVAS_DOMAIN_SCHEMA, canvas_domain_contract
from app.domains.finance import FINANCE_DOMAIN_SCHEMA, finance_domain_contract
from app.domains.narrative_risk import NARRATIVE_RISK_DOMAIN_SCHEMA, narrative_risk_domain_contract
from app.domains.global_impact import GLOBAL_IMPACT_DOMAIN_SCHEMA, global_impact_domain_contract

UNIFIED_DECISION_MODULE_REGISTRY_SCHEMA = "scds-unified-decision-module-registry/1.0"
UNIFIED_DECISION_MODULE_REGISTRY_VERSION = "1.0"
CANONICAL_MODULE_IDS = ("canvas", "finance", "narrative-risk", "global-impact")

_ROUTE_PREFIXES = {
    "canvas": "/canvas",
    "finance": "/finance",
    "narrative-risk": "/narrative-risk",
    "global-impact": "/global-impact",
}

_DOMAIN_CONTRACT_BUILDERS = {
    "canvas": canvas_domain_contract,
    "finance": finance_domain_contract,
    "narrative-risk": narrative_risk_domain_contract,
    "global-impact": global_impact_domain_contract,
}

_DOMAIN_SCHEMAS = {
    "canvas": CANVAS_DOMAIN_SCHEMA,
    "finance": FINANCE_DOMAIN_SCHEMA,
    "narrative-risk": NARRATIVE_RISK_DOMAIN_SCHEMA,
    "global-impact": GLOBAL_IMPACT_DOMAIN_SCHEMA,
}


class UnifiedRegistryValidateRequest(BaseModel):
    registry: dict[str, Any] = Field(default_factory=dict)
    strict: bool = True


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(x) for x in value]
    return [str(value)]


def _compute_authority(base: dict[str, Any], domain: dict[str, Any]) -> str | None:
    direct = domain.get("compute_authority")
    if direct:
        return str(direct)
    providers = base.get("providers") or {}
    if isinstance(providers, dict) and providers.get("compute_authority"):
        return str(providers["compute_authority"])
    return None


def unified_module_entry(module_id: str) -> dict[str, Any] | None:
    module_id = str(module_id or "").strip().lower()
    base = module_contract(module_id)
    builder = _DOMAIN_CONTRACT_BUILDERS.get(module_id)
    if not base or builder is None:
        return None
    domain = builder()
    security = deepcopy(domain.get("security") or {})
    compute_authority = _compute_authority(base, domain)
    providers = deepcopy(base.get("providers") or {})
    compatibility = deepcopy(domain.get("compatibility") or {})
    boundaries = deepcopy(domain.get("boundaries") or {})
    return {
        "module_id": module_id,
        "display_name": base.get("display_name"),
        "domain": base.get("domain"),
        "purpose": base.get("purpose"),
        "status": domain.get("status", base.get("status")),
        "route_prefix": _ROUTE_PREFIXES[module_id],
        "schemas": {
            "kernel": DECISION_KERNEL_SCHEMA,
            "module_contract": DECISION_MODULE_CONTRACT_SCHEMA,
            "legacy_registry": DECISION_MODULE_REGISTRY_SCHEMA,
            "domain": domain.get("schema") or _DOMAIN_SCHEMAS[module_id],
            "repository": domain.get("repository_schema", "scds-python-decision-repository/1.0"),
        },
        "authority": {
            "registration": "decision-studio-kernel",
            "storage": domain.get("storage_authority", base.get("storage_authority")),
            "compute": compute_authority,
            "final_decision": "human-governed",
        },
        "extends_kernel_objects": deepcopy(base.get("extends_kernel_objects") or []),
        "capabilities": deepcopy(base.get("capabilities") or []),
        "providers": providers,
        "normalized_postgresql_tables": deepcopy(domain.get("normalized_postgresql_tables") or []),
        "security": security,
        "compatibility": compatibility,
        "boundaries": boundaries,
        "endpoints": {
            "domain_contract": f"{_ROUTE_PREFIXES[module_id]}/contract",
            "legacy_module_contract": f"/decision-modules/{module_id}",
            "unified_registry_entry": f"/decision-module-registry/modules/{module_id}",
        },
    }


def unified_modules() -> list[dict[str, Any]]:
    return [unified_module_entry(mid) for mid in CANONICAL_MODULE_IDS]  # type: ignore[list-item]


def capability_index() -> dict[str, Any]:
    index: dict[str, list[str]] = {}
    for module in unified_modules():
        for capability in module["capabilities"]:
            index.setdefault(str(capability), []).append(module["module_id"])
    return {
        "schema": UNIFIED_DECISION_MODULE_REGISTRY_SCHEMA,
        "capability_count": len(index),
        "capabilities": [
            {"capability": capability, "modules": sorted(modules)}
            for capability, modules in sorted(index.items())
        ],
    }


def provider_index() -> dict[str, Any]:
    providers: dict[str, dict[str, set[str]]] = {}
    for module in unified_modules():
        for role, values in (module.get("providers") or {}).items():
            for provider in _as_list(values):
                entry = providers.setdefault(provider, {"roles": set(), "modules": set()})
                entry["roles"].add(str(role))
                entry["modules"].add(module["module_id"])
        compute = module["authority"].get("compute")
        if compute:
            entry = providers.setdefault(str(compute), {"roles": set(), "modules": set()})
            entry["roles"].add("compute_authority")
            entry["modules"].add(module["module_id"])
    return {
        "schema": UNIFIED_DECISION_MODULE_REGISTRY_SCHEMA,
        "provider_count": len(providers),
        "providers": [
            {
                "provider": provider,
                "roles": sorted(values["roles"]),
                "modules": sorted(values["modules"]),
            }
            for provider, values in sorted(providers.items())
        ],
    }


def registry_readiness(persistence: dict[str, Any] | None = None) -> dict[str, Any]:
    modules = unified_modules()
    all_authoritative = all(m["status"] == "python-domain-authoritative" for m in modules)
    persistence = deepcopy(persistence or {})
    persistence_ready = bool(
        persistence.get("connected")
        and persistence.get("schema_current")
        and persistence.get("authority_ready")
        and persistence.get("authority") == "python-postgresql"
    ) if persistence else None
    ready = all_authoritative if persistence_ready is None else bool(all_authoritative and persistence_ready)
    return {
        "schema": UNIFIED_DECISION_MODULE_REGISTRY_SCHEMA,
        "ready": ready,
        "module_count": len(modules),
        "authoritative_module_count": sum(m["status"] == "python-domain-authoritative" for m in modules),
        "all_modules_authoritative": all_authoritative,
        "persistence_ready": persistence_ready,
        "storage_authority": "python-postgresql",
        "compute_authorities": {
            m["module_id"]: m["authority"]["compute"]
            for m in modules if m["authority"].get("compute")
        },
        "final_decision_authority": "human-governed",
        "modules": [
            {
                "module_id": m["module_id"],
                "status": m["status"],
                "domain_schema": m["schemas"]["domain"],
                "storage_authority": m["authority"]["storage"],
                "compute_authority": m["authority"].get("compute"),
                "read_scope": m["security"].get("read_scope"),
                "write_scope": m["security"].get("write_scope"),
                "ready": m["status"] == "python-domain-authoritative" and m["authority"]["storage"] == "python-postgresql",
            }
            for m in modules
        ],
    }


def unified_registry(persistence: dict[str, Any] | None = None) -> dict[str, Any]:
    legacy = module_registry()
    modules = unified_modules()
    return {
        "schema": UNIFIED_DECISION_MODULE_REGISTRY_SCHEMA,
        "version": UNIFIED_DECISION_MODULE_REGISTRY_VERSION,
        "registry_role": "canonical-module-discovery-and-readiness-control-plane",
        "registry_authority": "decision-studio-kernel",
        "kernel_schema": DECISION_KERNEL_SCHEMA,
        "module_contract_schema": DECISION_MODULE_CONTRACT_SCHEMA,
        "legacy_registry_schema": DECISION_MODULE_REGISTRY_SCHEMA,
        "module_count": len(modules),
        "module_ids": [m["module_id"] for m in modules],
        "modules": modules,
        "capability_index": capability_index(),
        "provider_index": provider_index(),
        "readiness": registry_readiness(persistence),
        "compatibility": {
            "legacy_decision_modules_endpoints_preserved": True,
            "legacy_registry_module_count": legacy["module_count"],
            "legacy_registry_module_ids": [m["module_id"] for m in legacy["modules"]],
            "domain_contract_endpoints_preserved": True,
            "public_api_breaking_change": False,
        },
        "governance": {
            "registry_does_not_execute_domain_computation": True,
            "registry_does_not_change_module_storage_authority": True,
            "registry_does_not_infer_truth_or_causality": True,
            "registry_does_not_auto_recommend": True,
            "registry_does_not_auto_approve": True,
            "final_decision_authority": "human-governed",
        },
    }


def validate_unified_registry(payload: dict[str, Any], strict: bool = True) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(payload, dict):
        return {"ok": False, "errors": ["registry_must_be_object"], "warnings": []}
    if payload.get("schema") not in (None, UNIFIED_DECISION_MODULE_REGISTRY_SCHEMA):
        errors.append("unexpected_registry_schema")
    raw_modules = payload.get("modules")
    if not isinstance(raw_modules, list):
        errors.append("modules_must_be_list")
        raw_modules = []
    ids = [str(m.get("module_id")) for m in raw_modules if isinstance(m, dict) and m.get("module_id")]
    expected = list(CANONICAL_MODULE_IDS)
    if len(ids) != len(set(ids)):
        errors.append("duplicate_module_id")
    missing = [mid for mid in expected if mid not in ids]
    unknown = [mid for mid in ids if mid not in expected]
    if missing:
        errors.append("missing_modules:" + ",".join(missing))
    if unknown:
        errors.append("unknown_modules:" + ",".join(unknown))
    for item in raw_modules:
        if not isinstance(item, dict) or item.get("module_id") not in expected:
            continue
        module_id = str(item["module_id"])
        expected_entry = unified_module_entry(module_id) or {}
        if item.get("status") not in (None, "python-domain-authoritative"):
            errors.append(f"{module_id}:status_not_authoritative")
        authority = item.get("authority") or {}
        if authority and authority.get("storage") != "python-postgresql":
            errors.append(f"{module_id}:storage_authority_mismatch")
        schemas = item.get("schemas") or {}
        if schemas and schemas.get("domain") != expected_entry.get("schemas", {}).get("domain"):
            errors.append(f"{module_id}:domain_schema_mismatch")
    if strict and payload.get("module_count") not in (None, len(expected)):
        errors.append("module_count_mismatch")
    if not strict and not raw_modules:
        warnings.append("empty_registry")
    return {
        "ok": not errors,
        "schema": UNIFIED_DECISION_MODULE_REGISTRY_SCHEMA,
        "errors": errors,
        "warnings": warnings,
        "expected_module_ids": expected,
    }
