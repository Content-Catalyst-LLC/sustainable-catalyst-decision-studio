from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.canvas import CANVAS_OBJECT_TYPE, CanvasDomainRepository
from app.domains.finance import FINANCE_OBJECT_TYPE, FinanceDomainRepository
from app.domains.narrative_risk import NARRATIVE_RISK_OBJECT_TYPE, NarrativeRiskDomainRepository
from app.domains.global_impact import GLOBAL_IMPACT_OBJECT_TYPE, GlobalImpactDomainRepository
from app.persistence.models import DecisionObject
from app.persistence.repository import PersistenceRepository
from app.unified_module_registry import CANONICAL_MODULE_IDS, UNIFIED_DECISION_MODULE_REGISTRY_SCHEMA

CROSS_MODULE_COMPOSITION_SCHEMA = "scds-cross-module-decision-composition/1.0"
CROSS_MODULE_COMPOSITION_VERSION = "1.0"
CROSS_MODULE_COMPOSITION_OBJECT_TYPE = "cross-module-decision-composition"

_DOMAIN_OBJECT_TYPES = {
    "canvas": CANVAS_OBJECT_TYPE,
    "finance": FINANCE_OBJECT_TYPE,
    "narrative-risk": NARRATIVE_RISK_OBJECT_TYPE,
    "global-impact": GLOBAL_IMPACT_OBJECT_TYPE,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _fingerprint(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(raw).hexdigest()


def composition_contract() -> dict[str, Any]:
    return {
        "schema": CROSS_MODULE_COMPOSITION_SCHEMA,
        "version": CROSS_MODULE_COMPOSITION_VERSION,
        "registry_schema": UNIFIED_DECISION_MODULE_REGISTRY_SCHEMA,
        "role": "governed-cross-module-decision-composition",
        "canonical_modules": list(CANONICAL_MODULE_IDS),
        "minimum_modules": 2,
        "storage_authority": "python-postgresql",
        "final_decision_authority": "human-governed",
        "principles": {
            "shared_decision_identity_owned_by_kernel": True,
            "module_objects_retain_domain_ownership": True,
            "composition_links_are_explicit_not_inferred": True,
            "composition_does_not_merge_contradictory_claims": True,
            "composition_does_not_infer_causality": True,
            "composition_does_not_execute_domain_models": True,
            "composition_does_not_auto_select_winner": True,
            "composition_does_not_auto_recommend": True,
            "composition_does_not_auto_approve": True,
        },
        "compute_authorities": {
            "finance": "workbench",
            "global-impact": "workbench",
        },
        "security": {
            "read_scope": "composition:read",
            "write_scope": "composition:write",
            "repository_key_also_authorized": True,
        },
        "persistence": {
            "table": "decision_objects",
            "object_type": CROSS_MODULE_COMPOSITION_OBJECT_TYPE,
            "schema_migration_required": False,
        },
    }


def composition_template(decision_id: str = "") -> dict[str, Any]:
    return {
        "schema": CROSS_MODULE_COMPOSITION_SCHEMA,
        "version": CROSS_MODULE_COMPOSITION_VERSION,
        "decision_id": decision_id,
        "title": "",
        "purpose": "",
        "selected_modules": list(CANONICAL_MODULE_IDS),
        "module_snapshots": {},
        "module_fingerprints": {},
        "shared_kernel_projection": {
            "alternatives": [],
            "criteria": [],
            "assumptions": [],
            "claims": [],
            "evidence_links": [],
            "artifacts": [],
            "scenarios": [],
        },
        "cross_module_links": [],
        "diagnostics": {},
        "notes": [],
        "provenance": {
            "source": "cross-module-decision-composition",
            "records": [],
        },
        "boundaries": deepcopy(composition_contract()["principles"]),
        "authorities": {
            "storage": "python-postgresql",
            "finance_compute": "workbench",
            "global_impact_compute": "workbench",
            "final_decision": "human-governed",
        },
    }


class CrossModuleLink(BaseModel):
    relation: str = Field(min_length=1, max_length=96)
    source_module: str = Field(min_length=1, max_length=64)
    source_ref: str = Field(min_length=1, max_length=255)
    target_module: str = Field(min_length=1, max_length=64)
    target_ref: str = Field(min_length=1, max_length=255)
    note: str = Field(default="", max_length=2000)
    provenance_ref: str | None = Field(default=None, max_length=255)


class CompositionUpsertRequest(BaseModel):
    module_ids: list[str] = Field(default_factory=lambda: list(CANONICAL_MODULE_IDS))
    title: str = Field(default="", max_length=300)
    purpose: str = Field(default="", max_length=4000)
    cross_module_links: list[CrossModuleLink] = Field(default_factory=list)
    notes: list[Any] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    provenance_ref: str | None = Field(default=None, max_length=255)


class CompositionValidateRequest(BaseModel):
    composition: dict[str, Any] = Field(default_factory=dict)
    strict: bool = True


def _normalize_module_ids(module_ids: list[str] | tuple[str, ...]) -> list[str]:
    cleaned: list[str] = []
    for raw in module_ids:
        mid = str(raw or "").strip().lower()
        if mid and mid not in cleaned:
            cleaned.append(mid)
    return cleaned


def validate_composition_document(composition: dict[str, Any], strict: bool = True) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if composition.get("schema") != CROSS_MODULE_COMPOSITION_SCHEMA:
        errors.append("schema_mismatch")
    module_ids = _normalize_module_ids(composition.get("selected_modules") or [])
    unknown = sorted(set(module_ids) - set(CANONICAL_MODULE_IDS))
    if unknown:
        errors.append("unknown_modules:" + ",".join(unknown))
    if len(module_ids) < 2:
        errors.append("at_least_two_modules_required")
    snapshots = composition.get("module_snapshots") or {}
    if strict:
        for module_id in module_ids:
            if module_id not in snapshots:
                errors.append(f"missing_module_snapshot:{module_id}")
    for idx, link in enumerate(composition.get("cross_module_links") or []):
        if not isinstance(link, dict):
            errors.append(f"invalid_link:{idx}")
            continue
        source_module = str(link.get("source_module") or "").strip().lower()
        target_module = str(link.get("target_module") or "").strip().lower()
        if source_module not in module_ids or target_module not in module_ids:
            errors.append(f"link_module_not_selected:{idx}")
        if source_module == target_module:
            errors.append(f"link_must_be_cross_module:{idx}")
        if not str(link.get("source_ref") or "").strip() or not str(link.get("target_ref") or "").strip():
            errors.append(f"link_ref_required:{idx}")
    diagnostics = composition.get("diagnostics") or {}
    if diagnostics.get("inferred_truth") is True or diagnostics.get("inferred_causality") is True:
        errors.append("forbidden_inference_flag")
    if not composition.get("cross_module_links"):
        warnings.append("no_explicit_cross_module_links")
    return {"ok": not errors, "errors": errors, "warnings": warnings, "schema": CROSS_MODULE_COMPOSITION_SCHEMA}


class CrossModuleCompositionRepository:
    def __init__(self, session: Session):
        self.session = session
        self.repository = PersistenceRepository(session)

    def _require_decision(self, decision_id: str):
        row = self.repository.get_decision(decision_id)
        if not row:
            raise LookupError("decision_not_found")
        return row

    def _composition_object(self, decision_id: str) -> DecisionObject | None:
        return self.session.scalar(select(DecisionObject).where(
            DecisionObject.decision_id == decision_id,
            DecisionObject.object_type == CROSS_MODULE_COMPOSITION_OBJECT_TYPE,
        ))

    def _domain_object_exists(self, decision_id: str, module_id: str) -> bool:
        return self.session.scalar(select(DecisionObject.id).where(
            DecisionObject.decision_id == decision_id,
            DecisionObject.object_type == _DOMAIN_OBJECT_TYPES[module_id],
        ).limit(1)) is not None

    def _module_state(self, decision_id: str, module_id: str) -> dict[str, Any]:
        if module_id == "canvas":
            return CanvasDomainRepository(self.session).get_canvas(decision_id)
        if module_id == "finance":
            return FinanceDomainRepository(self.session).get_finance(decision_id)
        if module_id == "narrative-risk":
            return NarrativeRiskDomainRepository(self.session).get_narrative_risk(decision_id)
        if module_id == "global-impact":
            return GlobalImpactDomainRepository(self.session).get_global_impact(decision_id)
        raise ValueError("unknown_module")

    @staticmethod
    def _owned(module_id: str, object_type: str, items: list[Any]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for idx, raw in enumerate(items or []):
            item = deepcopy(raw) if isinstance(raw, dict) else {"value": raw}
            ref = str(item.get("id") or item.get("artifact_id") or item.get("evidence_ref") or item.get("name") or item.get("label") or f"{object_type}-{idx}")
            result.append({"module_id": module_id, "object_type": object_type, "ref": ref, "value": item})
        return result

    def _shared_projection(self, states: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        projection = {k: [] for k in ("alternatives", "criteria", "assumptions", "claims", "evidence_links", "artifacts", "scenarios")}
        canvas = states.get("canvas") or {}
        projection["alternatives"] += self._owned("canvas", "alternative", canvas.get("alternatives") or [])
        projection["criteria"] += self._owned("canvas", "criterion", canvas.get("criteria") or [])
        projection["assumptions"] += self._owned("canvas", "assumption", canvas.get("assumptions") or [])

        finance = states.get("finance") or {}
        projection["assumptions"] += self._owned("finance", "assumption", finance.get("assumptions") or [])
        projection["scenarios"] += self._owned("finance", "scenario", finance.get("scenarios") or [])
        projection["artifacts"] += self._owned("finance", "workbench-receipt", finance.get("workbench_receipts") or [])

        risk = states.get("narrative-risk") or {}
        projection["claims"] += self._owned("narrative-risk", "claim", risk.get("claims") or [])
        projection["evidence_links"] += self._owned("narrative-risk", "evidence-link", risk.get("evidence_links") or [])
        projection["artifacts"] += self._owned("narrative-risk", "signal", risk.get("signals") or [])

        impact = states.get("global-impact") or {}
        projection["claims"] += self._owned("global-impact", "impact-claim", impact.get("impact_claims") or [])
        projection["evidence_links"] += self._owned("global-impact", "evidence-link", impact.get("evidence_links") or [])
        projection["artifacts"] += self._owned("global-impact", "impact-indicator", impact.get("indicators") or [])
        return projection

    def _diagnostics_for(self, decision_id: str, module_ids: list[str], states: dict[str, dict[str, Any]], links: list[dict[str, Any]], stored_fingerprints: dict[str, str] | None = None) -> dict[str, Any]:
        present = {mid: self._domain_object_exists(decision_id, mid) for mid in module_ids}
        fingerprints = {mid: _fingerprint(states[mid]) for mid in module_ids}
        stale_modules = []
        if stored_fingerprints:
            stale_modules = [mid for mid in module_ids if stored_fingerprints.get(mid) != fingerprints.get(mid)]
        relation_counts: dict[str, int] = {}
        for link in links:
            relation = str(link.get("relation") or "unspecified")
            relation_counts[relation] = relation_counts.get(relation, 0) + 1
        return {
            "selected_module_count": len(module_ids),
            "present_module_count": sum(present.values()),
            "module_state_present": present,
            "missing_module_states": [mid for mid, ok in present.items() if not ok],
            "composition_ready": len(module_ids) >= 2 and all(present.values()),
            "cross_module_link_count": len(links),
            "declared_relation_counts": relation_counts,
            "module_fingerprints": fingerprints,
            "stale_modules": stale_modules,
            "inferred_truth": False,
            "inferred_causality": False,
            "automatic_recommendation": False,
            "automatic_approval": False,
        }

    def build(self, decision_id: str, request: CompositionUpsertRequest, *, revision: int = 1) -> dict[str, Any]:
        decision = self._require_decision(decision_id)
        module_ids = _normalize_module_ids(request.module_ids)
        unknown = sorted(set(module_ids) - set(CANONICAL_MODULE_IDS))
        if unknown:
            raise ValueError("unknown_modules:" + ",".join(unknown))
        if len(module_ids) < 2:
            raise ValueError("at_least_two_modules_required")
        links = [link.model_dump() for link in request.cross_module_links]
        for idx, link in enumerate(links):
            if link["source_module"] not in module_ids or link["target_module"] not in module_ids:
                raise ValueError(f"link_module_not_selected:{idx}")
            if link["source_module"] == link["target_module"]:
                raise ValueError(f"link_must_be_cross_module:{idx}")
        states = {mid: self._module_state(decision_id, mid) for mid in module_ids}
        fingerprints = {mid: _fingerprint(states[mid]) for mid in module_ids}
        diagnostics = self._diagnostics_for(decision_id, module_ids, states, links)
        result = composition_template(decision_id)
        result.update({
            "revision": revision,
            "decision_question": decision.decision_question,
            "title": request.title,
            "purpose": request.purpose,
            "selected_modules": module_ids,
            "module_snapshots": states,
            "module_fingerprints": fingerprints,
            "shared_kernel_projection": self._shared_projection(states),
            "cross_module_links": links,
            "diagnostics": diagnostics,
            "notes": deepcopy(request.notes),
            "provenance": {**composition_template(decision_id)["provenance"], **deepcopy(request.provenance), "composed_at": _now()},
        })
        return result

    def upsert(self, decision_id: str, request: CompositionUpsertRequest) -> dict[str, Any]:
        self._require_decision(decision_id)
        existing = self._composition_object(decision_id)
        prior_revision = int((existing.payload or {}).get("revision", 0)) if existing else 0
        composition = self.build(decision_id, request, revision=prior_revision + 1)
        validation = validate_composition_document(composition, strict=True)
        if not validation["ok"]:
            raise ValueError("composition_invalid:" + ";".join(validation["errors"]))
        if existing is None:
            oid = f"cmp_{sha256(decision_id.encode('utf-8')).hexdigest()[:24]}"
            existing = DecisionObject(
                id=oid,
                decision_id=decision_id,
                object_type=CROSS_MODULE_COMPOSITION_OBJECT_TYPE,
                schema_id=CROSS_MODULE_COMPOSITION_SCHEMA,
                payload=composition,
                provenance_ref=request.provenance_ref,
            )
            self.session.add(existing)
            event = "decision_composition.created"
        else:
            existing.schema_id = CROSS_MODULE_COMPOSITION_SCHEMA
            existing.payload = composition
            existing.provenance_ref = request.provenance_ref
            event = "decision_composition.updated"
        self.session.flush()
        self.repository._event(decision_id, event, {
            "schema": CROSS_MODULE_COMPOSITION_SCHEMA,
            "revision": composition["revision"],
            "modules": composition["selected_modules"],
            "cross_module_link_count": len(composition["cross_module_links"]),
        })
        return composition

    def get(self, decision_id: str) -> dict[str, Any] | None:
        self._require_decision(decision_id)
        obj = self._composition_object(decision_id)
        return deepcopy(obj.payload or {}) if obj else None

    def refresh(self, decision_id: str) -> dict[str, Any]:
        obj = self._composition_object(decision_id)
        if obj is None:
            raise LookupError("composition_not_found")
        payload = deepcopy(obj.payload or {})
        request = CompositionUpsertRequest(
            module_ids=payload.get("selected_modules") or list(CANONICAL_MODULE_IDS),
            title=str(payload.get("title") or ""),
            purpose=str(payload.get("purpose") or ""),
            cross_module_links=payload.get("cross_module_links") or [],
            notes=payload.get("notes") or [],
            provenance=payload.get("provenance") or {},
            provenance_ref=obj.provenance_ref,
        )
        composition = self.build(decision_id, request, revision=int(payload.get("revision", 0)) + 1)
        obj.payload = composition
        obj.schema_id = CROSS_MODULE_COMPOSITION_SCHEMA
        self.session.flush()
        self.repository._event(decision_id, "decision_composition.refreshed", {
            "revision": composition["revision"],
            "modules": composition["selected_modules"],
        })
        return composition

    def diagnostics(self, decision_id: str) -> dict[str, Any]:
        composition = self.get(decision_id)
        if composition is None:
            raise LookupError("composition_not_found")
        module_ids = _normalize_module_ids(composition.get("selected_modules") or [])
        states = {mid: self._module_state(decision_id, mid) for mid in module_ids}
        return self._diagnostics_for(
            decision_id,
            module_ids,
            states,
            composition.get("cross_module_links") or [],
            stored_fingerprints=composition.get("module_fingerprints") or {},
        )
