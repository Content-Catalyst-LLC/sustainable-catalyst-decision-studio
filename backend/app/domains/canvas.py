from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.persistence.models import Alternative, Assumption, Criterion, DecisionObject
from app.persistence.repository import PersistenceRepository

CANVAS_DOMAIN_SCHEMA = "scds-canvas-domain/1.0"
CANVAS_DOMAIN_VERSION = "1.0"
CANVAS_MODULE_ID = "canvas"
CANVAS_OBJECT_TYPE = "canvas-domain"


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:24]}"


def _domain_id(decision_id: str, prefix: str, source_id: Any | None = None) -> str:
    if source_id not in (None, ""):
        raw = f"{decision_id}:{prefix}:{source_id}".encode("utf-8")
        return f"{prefix}_{sha256(raw).hexdigest()[:24]}"
    return _id(prefix)


def canvas_domain_contract() -> dict[str, Any]:
    return {
        "schema": CANVAS_DOMAIN_SCHEMA,
        "version": CANVAS_DOMAIN_VERSION,
        "module_id": CANVAS_MODULE_ID,
        "display_name": "Canvas",
        "status": "python-domain-authoritative",
        "storage_authority": "python-postgresql",
        "kernel_contract_schema": "scds-decision-kernel/1.0",
        "repository_schema": "scds-python-decision-repository/1.0",
        "owns": [
            "problem-framing",
            "objective-and-constraints",
            "stakeholder-context",
            "alternatives",
            "criteria",
            "assumptions",
            "success-measures",
            "framing-provenance",
        ],
        "shared_kernel_objects": ["decision", "alternative", "criterion", "assumption", "evidence_ref", "scenario"],
        "normalized_postgresql_tables": ["alternatives", "criteria", "assumptions", "decision_objects", "decision_module_bindings", "decision_events"],
        "compatibility": {
            "legacy_catalyst_canvas_import": True,
            "legacy_wordpress_source_preserved": True,
            "typed_platform_artifact_adapter_preserved": True,
            "decision_packet_projection_preserved": True,
        },
        "boundaries": {
            "shared_decision_identity_owned_by_kernel": True,
            "final_decision_authority": "human-governed",
            "automatic_winner_selection": False,
            "automatic_recommendation": False,
            "automatic_approval": False,
            "finance_compute_authority_unchanged": "workbench",
        },
        "security": {
            "read_scope": "canvas:read",
            "write_scope": "canvas:write",
            "repository_key_also_authorized": True,
        },
    }


def canvas_domain_template(decision_id: str = "") -> dict[str, Any]:
    return {
        "schema": CANVAS_DOMAIN_SCHEMA,
        "version": CANVAS_DOMAIN_VERSION,
        "decision_id": decision_id,
        "problem_statement": "",
        "decision_question": "",
        "objective": "",
        "constraints": [],
        "stakeholders": [],
        "success_measures": [],
        "alternatives": [],
        "criteria": [],
        "assumptions": [],
        "evidence_refs": [],
        "scenario_refs": [],
        "notes": [],
        "provenance": {
            "source": "canvas-python-domain",
            "legacy_source_preserved": True,
            "records": [],
        },
        "boundaries": {
            "automatic_winner_selection": False,
            "automatic_recommendation": False,
            "final_decision_authority": "human-governed",
        },
    }


class CanvasStateUpsert(BaseModel):
    problem_statement: str = ""
    decision_question: str = ""
    objective: str = ""
    constraints: list[Any] = Field(default_factory=list)
    stakeholders: list[dict[str, Any]] = Field(default_factory=list)
    success_measures: list[Any] = Field(default_factory=list)
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    criteria: list[dict[str, Any]] = Field(default_factory=list)
    assumptions: list[dict[str, Any]] = Field(default_factory=list)
    evidence_refs: list[Any] = Field(default_factory=list)
    scenario_refs: list[Any] = Field(default_factory=list)
    notes: list[Any] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    provenance_ref: str | None = Field(default=None, max_length=255)


class CanvasAlternativesReplace(BaseModel):
    alternatives: list[dict[str, Any]] = Field(default_factory=list)


class CanvasCriteriaReplace(BaseModel):
    criteria: list[dict[str, Any]] = Field(default_factory=list)


class CanvasAssumptionsReplace(BaseModel):
    assumptions: list[dict[str, Any]] = Field(default_factory=list)


class CanvasLegacyImport(BaseModel):
    artifact: dict[str, Any] = Field(default_factory=dict)
    decision_id: str | None = Field(default=None, max_length=64)
    project_id: str | None = Field(default=None, max_length=64)
    project_title: str | None = Field(default=None, max_length=300)
    owner_ref: str | None = Field(default=None, max_length=255)
    provenance_ref: str | None = Field(default=None, max_length=255)


class CanvasDomainRepository:
    """Authoritative Canvas domain over the shared Decision Studio repository."""

    schema = CANVAS_DOMAIN_SCHEMA
    module_id = CANVAS_MODULE_ID

    def __init__(self, session: Session):
        self.session = session
        self.repository = PersistenceRepository(session)

    def _require_decision(self, decision_id: str):
        row = self.repository.get_decision(decision_id)
        if not row:
            raise LookupError("decision_not_found")
        return row

    def _canvas_object(self, decision_id: str) -> DecisionObject | None:
        return self.session.scalar(
            select(DecisionObject).where(
                DecisionObject.decision_id == decision_id,
                DecisionObject.object_type == CANVAS_OBJECT_TYPE,
            )
        )

    @staticmethod
    def _alternative_dict(row: Alternative) -> dict[str, Any]:
        return {
            "id": row.id,
            "name": row.name,
            "description": row.description or "",
            "status": row.status,
            "metadata": row.metadata_json,
        }

    @staticmethod
    def _criterion_dict(row: Criterion) -> dict[str, Any]:
        return {
            "id": row.id,
            "name": row.name,
            "weight": row.weight,
            "direction": row.direction,
            "metadata": row.metadata_json,
        }

    @staticmethod
    def _assumption_dict(row: Assumption) -> dict[str, Any]:
        return {
            "id": row.id,
            "statement": row.statement,
            "status": row.status,
            "confidence": row.confidence,
            "metadata": row.metadata_json,
        }

    def _refresh_object_lists(self, decision_id: str) -> None:
        obj = self._canvas_object(decision_id)
        if obj is None:
            return
        payload = deepcopy(obj.payload or {})
        payload["alternatives"] = self.list_alternatives(decision_id)
        payload["criteria"] = self.list_criteria(decision_id)
        payload["assumptions"] = self.list_assumptions(decision_id)
        obj.payload = payload
        self.session.flush()

    def list_alternatives(self, decision_id: str) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        rows = self.session.scalars(
            select(Alternative).where(Alternative.decision_id == decision_id).order_by(Alternative.created_at, Alternative.id)
        )
        return [self._alternative_dict(r) for r in rows]

    def list_criteria(self, decision_id: str) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        rows = self.session.scalars(
            select(Criterion).where(Criterion.decision_id == decision_id).order_by(Criterion.created_at, Criterion.id)
        )
        return [self._criterion_dict(r) for r in rows]

    def list_assumptions(self, decision_id: str) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        rows = self.session.scalars(
            select(Assumption).where(Assumption.decision_id == decision_id).order_by(Assumption.created_at, Assumption.id)
        )
        return [self._assumption_dict(r) for r in rows]

    def replace_alternatives(self, decision_id: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        for row in list(self.session.scalars(select(Alternative).where(Alternative.decision_id == decision_id))):
            self.session.delete(row)
        self.session.flush()
        for item in items:
            name = str(item.get("name") or item.get("title") or item.get("label") or "").strip()
            if not name:
                raise ValueError("alternative_name_required")
            self.session.add(Alternative(
                id=_domain_id(decision_id, "alt", item.get("id")),
                decision_id=decision_id,
                name=name[:300],
                description=str(item.get("description") or "") or None,
                status=str(item.get("status") or "candidate")[:64],
                metadata_json={**deepcopy(item.get("metadata") or {}), **({"source_id": str(item.get("id"))} if item.get("id") not in (None, "") else {})},
            ))
        self.session.flush()
        self._refresh_object_lists(decision_id)
        self.repository._event(decision_id, "canvas.alternatives.replaced", {"count": len(items)})
        return self.list_alternatives(decision_id)

    def replace_criteria(self, decision_id: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        for row in list(self.session.scalars(select(Criterion).where(Criterion.decision_id == decision_id))):
            self.session.delete(row)
        self.session.flush()
        for item in items:
            name = str(item.get("name") or item.get("title") or item.get("label") or "").strip()
            if not name:
                raise ValueError("criterion_name_required")
            weight = item.get("weight")
            self.session.add(Criterion(
                id=_domain_id(decision_id, "crit", item.get("id")),
                decision_id=decision_id,
                name=name[:300],
                weight=None if weight is None else str(weight)[:64],
                direction=(str(item.get("direction"))[:32] if item.get("direction") is not None else None),
                metadata_json={**deepcopy(item.get("metadata") or {}), **({"source_id": str(item.get("id"))} if item.get("id") not in (None, "") else {})},
            ))
        self.session.flush()
        self._refresh_object_lists(decision_id)
        self.repository._event(decision_id, "canvas.criteria.replaced", {"count": len(items)})
        return self.list_criteria(decision_id)

    def replace_assumptions(self, decision_id: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        for row in list(self.session.scalars(select(Assumption).where(Assumption.decision_id == decision_id))):
            self.session.delete(row)
        self.session.flush()
        for item in items:
            statement = str(item.get("statement") or item.get("text") or item.get("assumption") or "").strip()
            if not statement:
                raise ValueError("assumption_statement_required")
            confidence = item.get("confidence")
            self.session.add(Assumption(
                id=_domain_id(decision_id, "asm", item.get("id")),
                decision_id=decision_id,
                statement=statement,
                status=str(item.get("status") or "open")[:64],
                confidence=None if confidence is None else str(confidence)[:64],
                metadata_json={**deepcopy(item.get("metadata") or {}), **({"source_id": str(item.get("id"))} if item.get("id") not in (None, "") else {})},
            ))
        self.session.flush()
        self._refresh_object_lists(decision_id)
        self.repository._event(decision_id, "canvas.assumptions.replaced", {"count": len(items)})
        return self.list_assumptions(decision_id)

    def get_canvas(self, decision_id: str) -> dict[str, Any]:
        decision = self._require_decision(decision_id)
        obj = self._canvas_object(decision_id)
        state = canvas_domain_template(decision_id)
        if obj:
            state.update(deepcopy(obj.payload or {}))
        state["schema"] = CANVAS_DOMAIN_SCHEMA
        state["version"] = CANVAS_DOMAIN_VERSION
        state["decision_id"] = decision_id
        state["decision_question"] = decision.decision_question
        state["alternatives"] = self.list_alternatives(decision_id)
        state["criteria"] = self.list_criteria(decision_id)
        state["assumptions"] = self.list_assumptions(decision_id)
        return state

    def upsert_canvas(self, decision_id: str, request: CanvasStateUpsert) -> dict[str, Any]:
        decision = self._require_decision(decision_id)
        self.repository.bind_module(
            decision_id,
            CANVAS_MODULE_ID,
            enabled=True,
            configuration={"domain_schema": CANVAS_DOMAIN_SCHEMA, "storage_authority": "python-postgresql"},
        )
        if request.decision_question.strip():
            decision.decision_question = request.decision_question.strip()
        alternatives = self.replace_alternatives(decision_id, request.alternatives)
        criteria = self.replace_criteria(decision_id, request.criteria)
        assumptions = self.replace_assumptions(decision_id, request.assumptions)
        state = canvas_domain_template(decision_id)
        state.update({
            "problem_statement": request.problem_statement,
            "decision_question": decision.decision_question,
            "objective": request.objective,
            "constraints": deepcopy(request.constraints),
            "stakeholders": deepcopy(request.stakeholders),
            "success_measures": deepcopy(request.success_measures),
            "alternatives": alternatives,
            "criteria": criteria,
            "assumptions": assumptions,
            "evidence_refs": deepcopy(request.evidence_refs),
            "scenario_refs": deepcopy(request.scenario_refs),
            "notes": deepcopy(request.notes),
            "provenance": {**canvas_domain_template(decision_id)["provenance"], **deepcopy(request.provenance)},
        })
        obj = self._canvas_object(decision_id)
        if obj is None:
            obj = DecisionObject(
                id=_id("canvas"),
                decision_id=decision_id,
                object_type=CANVAS_OBJECT_TYPE,
                schema_id=CANVAS_DOMAIN_SCHEMA,
                payload=state,
                provenance_ref=request.provenance_ref,
            )
            self.session.add(obj)
            event = "canvas.domain.created"
        else:
            obj.schema_id = CANVAS_DOMAIN_SCHEMA
            obj.payload = state
            obj.provenance_ref = request.provenance_ref
            event = "canvas.domain.updated"
        self.session.flush()
        self.repository._event(decision_id, event, {
            "schema": CANVAS_DOMAIN_SCHEMA,
            "alternatives": len(alternatives),
            "criteria": len(criteria),
            "assumptions": len(assumptions),
        })
        return self.get_canvas(decision_id)

    def import_legacy(self, request: CanvasLegacyImport) -> tuple[dict[str, Any], bool]:
        artifact = deepcopy(request.artifact or {})
        if not artifact:
            raise ValueError("canvas_artifact_required")
        decision_id = request.decision_id or str(artifact.get("decision_id") or _id("dec"))[:64]
        decision = self.repository.get_decision(decision_id)
        created = decision is None
        if request.project_id and not self.repository.get_project(request.project_id):
            self.repository.create_project(
                project_id=request.project_id,
                title=request.project_title or "Imported Catalyst Canvas",
                owner_ref=request.owner_ref,
                metadata={"source": "legacy-catalyst-canvas"},
            )
        challenge = str(artifact.get("challenge") or artifact.get("point_of_view") or "Imported Catalyst Canvas decision")
        if decision is None:
            self.repository.create_decision(
                decision_id=decision_id,
                project_id=request.project_id,
                decision_question=challenge,
                lifecycle_state="framing",
                metadata={"legacy_source": "catalyst-canvas"},
            )
        constraints: list[Any] = []
        raw_constraint = artifact.get("constraint") or artifact.get("constraints")
        if isinstance(raw_constraint, list):
            constraints = deepcopy(raw_constraint)
        elif raw_constraint not in (None, ""):
            constraints = [raw_constraint]
        audience = artifact.get("audience")
        stakeholders = []
        if audience:
            stakeholders.append({"role": "audience", "name": str(audience)})
        success_measures = []
        if artifact.get("test_plan"):
            success_measures.append(deepcopy(artifact["test_plan"]))
        if artifact.get("prototype"):
            success_measures.append({"prototype": deepcopy(artifact["prototype"])})
        state = CanvasStateUpsert(
            problem_statement=str(artifact.get("challenge") or artifact.get("point_of_view") or ""),
            decision_question=challenge,
            objective=str(artifact.get("goal") or ""),
            constraints=constraints,
            stakeholders=stakeholders,
            success_measures=success_measures,
            alternatives=deepcopy(artifact.get("alternatives") or []),
            criteria=deepcopy(artifact.get("criteria") or []),
            assumptions=deepcopy(artifact.get("assumptions") or []),
            notes=deepcopy(artifact.get("how_might_we") or []),
            provenance={
                "source": "legacy-catalyst-canvas",
                "legacy_source_preserved": True,
                "legacy_artifact": artifact,
                "records": [{"type": "migration", "release": "3.5.0"}],
            },
            provenance_ref=request.provenance_ref,
        )
        result = self.upsert_canvas(decision_id, state)
        self.repository._event(decision_id, "canvas.legacy_imported", {"source_preserved": True})
        return result, created
