from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.persistence.models import (
    Artifact,
    Assumption,
    DecisionObject,
    Scenario,
    ScenarioVariable,
    UncertaintyModel,
)
from app.persistence.repository import PersistenceRepository

FINANCE_DOMAIN_SCHEMA = "scds-finance-domain/1.0"
FINANCE_DOMAIN_VERSION = "1.0"
FINANCE_MODULE_ID = "finance"
FINANCE_OBJECT_TYPE = "finance-domain"
FINANCE_RECEIPT_ARTIFACT_TYPE = "finance-workbench-receipt"
FINANCE_DOMAIN_MARKER = "finance"


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:24]}"


def _domain_id(decision_id: str, prefix: str, source_id: Any | None = None) -> str:
    if source_id not in (None, ""):
        raw = f"{decision_id}:{FINANCE_DOMAIN_MARKER}:{prefix}:{source_id}".encode("utf-8")
        return f"{prefix}_{sha256(raw).hexdigest()[:24]}"
    return _id(prefix)


def _is_finance_metadata(value: Any) -> bool:
    return isinstance(value, dict) and value.get("domain") == FINANCE_DOMAIN_MARKER


def finance_domain_contract() -> dict[str, Any]:
    return {
        "schema": FINANCE_DOMAIN_SCHEMA,
        "version": FINANCE_DOMAIN_VERSION,
        "module_id": FINANCE_MODULE_ID,
        "display_name": "Finance",
        "status": "python-domain-authoritative",
        "storage_authority": "python-postgresql",
        "compute_authority": "workbench",
        "kernel_contract_schema": "scds-decision-kernel/1.0",
        "repository_schema": "scds-python-decision-repository/1.0",
        "owns": [
            "financial-context",
            "financial-assumptions",
            "capital-and-discounting-context",
            "cost-and-revenue-context",
            "cash-flow-model-references",
            "valuation-and-cost-benefit-references",
            "financial-scenarios",
            "financial-uncertainty",
            "workbench-computation-receipts",
            "financial-provenance",
        ],
        "shared_kernel_objects": [
            "decision",
            "alternative",
            "criterion",
            "assumption",
            "scenario",
            "artifact_ref",
            "provenance_ref",
            "recommendation",
        ],
        "normalized_postgresql_tables": [
            "assumptions",
            "scenarios",
            "scenario_variables",
            "uncertainty_models",
            "artifacts",
            "decision_objects",
            "decision_module_bindings",
            "decision_events",
        ],
        "providers": {
            "compute_authority": "workbench",
            "datasets": ["workspace", "knowledge-library"],
            "research": ["research-librarian", "research-lab"],
        },
        "compatibility": {
            "legacy_catalyst_finance_import": True,
            "legacy_wordpress_source_preserved": True,
            "typed_platform_artifact_adapter_preserved": True,
            "decision_packet_projection_preserved": True,
            "workbench_handoff_contract_preserved": True,
        },
        "boundaries": {
            "shared_decision_identity_owned_by_kernel": True,
            "workbench_is_compute_authority": True,
            "decision_studio_executes_financial_models": False,
            "model_output_is_automatic_recommendation": False,
            "financial_score_is_final_decision_authority": False,
            "automatic_approval": False,
            "final_decision_authority": "human-governed",
        },
        "security": {
            "read_scope": "finance:read",
            "write_scope": "finance:write",
            "repository_key_also_authorized": True,
        },
    }


def finance_domain_template(decision_id: str = "") -> dict[str, Any]:
    return {
        "schema": FINANCE_DOMAIN_SCHEMA,
        "version": FINANCE_DOMAIN_VERSION,
        "decision_id": decision_id,
        "currency": "USD",
        "base_year": None,
        "horizon_years": None,
        "capital_context": {},
        "cost_context": {},
        "revenue_context": {},
        "discounting_context": {},
        "model_refs": [],
        "valuation_refs": [],
        "cost_benefit_refs": [],
        "assumptions": [],
        "scenarios": [],
        "uncertainty_models": [],
        "workbench_receipts": [],
        "evidence_refs": [],
        "notes": [],
        "provenance": {
            "source": "finance-python-domain",
            "legacy_source_preserved": True,
            "records": [],
        },
        "authorities": {
            "storage_authority": "python-postgresql",
            "compute_authority": "workbench",
            "final_decision_authority": "human-governed",
        },
        "boundaries": {
            "decision_studio_executes_financial_models": False,
            "automatic_recommendation": False,
            "automatic_approval": False,
        },
    }


class FinanceStateUpsert(BaseModel):
    currency: str = Field(default="USD", max_length=16)
    base_year: int | None = None
    horizon_years: int | None = Field(default=None, ge=1, le=200)
    capital_context: dict[str, Any] = Field(default_factory=dict)
    cost_context: dict[str, Any] = Field(default_factory=dict)
    revenue_context: dict[str, Any] = Field(default_factory=dict)
    discounting_context: dict[str, Any] = Field(default_factory=dict)
    model_refs: list[Any] = Field(default_factory=list)
    valuation_refs: list[Any] = Field(default_factory=list)
    cost_benefit_refs: list[Any] = Field(default_factory=list)
    assumptions: list[dict[str, Any]] = Field(default_factory=list)
    scenarios: list[dict[str, Any]] = Field(default_factory=list)
    uncertainty_models: list[dict[str, Any]] = Field(default_factory=list)
    workbench_receipts: list[dict[str, Any]] = Field(default_factory=list)
    evidence_refs: list[Any] = Field(default_factory=list)
    notes: list[Any] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    provenance_ref: str | None = Field(default=None, max_length=255)


class FinanceAssumptionsReplace(BaseModel):
    assumptions: list[dict[str, Any]] = Field(default_factory=list)


class FinanceScenariosReplace(BaseModel):
    scenarios: list[dict[str, Any]] = Field(default_factory=list)


class FinanceWorkbenchReceiptsReplace(BaseModel):
    workbench_receipts: list[dict[str, Any]] = Field(default_factory=list)


class FinanceLegacyImport(BaseModel):
    artifact: dict[str, Any] = Field(default_factory=dict)
    decision_id: str | None = Field(default=None, max_length=64)
    project_id: str | None = Field(default=None, max_length=64)
    project_title: str | None = Field(default=None, max_length=300)
    owner_ref: str | None = Field(default=None, max_length=255)
    provenance_ref: str | None = Field(default=None, max_length=255)


class FinanceDomainRepository:
    """Authoritative Finance domain state with Workbench-retained compute authority."""

    schema = FINANCE_DOMAIN_SCHEMA
    module_id = FINANCE_MODULE_ID

    def __init__(self, session: Session):
        self.session = session
        self.repository = PersistenceRepository(session)

    def _require_decision(self, decision_id: str):
        row = self.repository.get_decision(decision_id)
        if not row:
            raise LookupError("decision_not_found")
        return row

    def _finance_object(self, decision_id: str) -> DecisionObject | None:
        return self.session.scalar(
            select(DecisionObject).where(
                DecisionObject.decision_id == decision_id,
                DecisionObject.object_type == FINANCE_OBJECT_TYPE,
            )
        )

    @staticmethod
    def _assumption_dict(row: Assumption) -> dict[str, Any]:
        metadata = deepcopy(row.metadata_json or {})
        return {
            "id": row.id,
            "statement": row.statement,
            "status": row.status,
            "confidence": row.confidence,
            "metadata": metadata,
        }

    @staticmethod
    def _scenario_dict(row: Scenario, variables: list[ScenarioVariable]) -> dict[str, Any]:
        return {
            "id": row.id,
            "name": row.name,
            "description": row.description or "",
            "status": row.status,
            "metadata": deepcopy(row.metadata_json or {}),
            "variables": [
                {
                    "id": v.id,
                    "name": v.name,
                    "value": deepcopy(v.value_json or {}),
                    "source_ref": v.source_ref,
                }
                for v in variables
            ],
        }

    @staticmethod
    def _uncertainty_dict(row: UncertaintyModel) -> dict[str, Any]:
        spec = deepcopy(row.specification or {})
        return {
            "id": row.id,
            "model_type": row.model_type,
            "specification": spec,
            "computation_ref": row.computation_ref,
            "provenance_ref": row.provenance_ref,
        }

    @staticmethod
    def _receipt_dict(row: Artifact) -> dict[str, Any]:
        return {
            "id": row.id,
            "artifact_type": row.artifact_type,
            "schema_id": row.schema_id,
            "uri": row.uri,
            "checksum_sha256": row.checksum_sha256,
            "provenance_ref": row.provenance_ref,
            "metadata": deepcopy(row.metadata_json or {}),
        }

    def _finance_assumption_rows(self, decision_id: str) -> list[Assumption]:
        rows = list(self.session.scalars(select(Assumption).where(Assumption.decision_id == decision_id).order_by(Assumption.created_at, Assumption.id)))
        return [r for r in rows if _is_finance_metadata(r.metadata_json)]

    def _finance_scenario_rows(self, decision_id: str) -> list[Scenario]:
        rows = list(self.session.scalars(select(Scenario).where(Scenario.decision_id == decision_id).order_by(Scenario.created_at, Scenario.id)))
        return [r for r in rows if _is_finance_metadata(r.metadata_json)]

    def _finance_uncertainty_rows(self, decision_id: str) -> list[UncertaintyModel]:
        rows = list(self.session.scalars(select(UncertaintyModel).where(UncertaintyModel.decision_id == decision_id).order_by(UncertaintyModel.created_at, UncertaintyModel.id)))
        return [r for r in rows if isinstance(r.specification, dict) and r.specification.get("domain") == FINANCE_DOMAIN_MARKER]

    def _finance_receipt_rows(self, decision_id: str) -> list[Artifact]:
        rows = list(self.session.scalars(select(Artifact).where(
            Artifact.decision_id == decision_id,
            Artifact.artifact_type == FINANCE_RECEIPT_ARTIFACT_TYPE,
        ).order_by(Artifact.created_at, Artifact.id)))
        return [r for r in rows if _is_finance_metadata(r.metadata_json)]

    def list_assumptions(self, decision_id: str) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        return [self._assumption_dict(r) for r in self._finance_assumption_rows(decision_id)]

    def replace_assumptions(self, decision_id: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        for row in self._finance_assumption_rows(decision_id):
            self.session.delete(row)
        self.session.flush()
        for item in items:
            statement = str(item.get("statement") or item.get("text") or item.get("assumption") or "").strip()
            if not statement:
                raise ValueError("finance_assumption_statement_required")
            metadata = deepcopy(item.get("metadata") or {})
            metadata["domain"] = FINANCE_DOMAIN_MARKER
            if item.get("id") not in (None, ""):
                metadata["source_id"] = str(item.get("id"))
            self.session.add(Assumption(
                id=_domain_id(decision_id, "fasm", item.get("id")),
                decision_id=decision_id,
                statement=statement,
                status=str(item.get("status") or "open")[:64],
                confidence=None if item.get("confidence") is None else str(item.get("confidence"))[:64],
                metadata_json=metadata,
            ))
        self.session.flush()
        self._refresh_object_lists(decision_id)
        self.repository._event(decision_id, "finance.assumptions.replaced", {"count": len(items)})
        return self.list_assumptions(decision_id)

    def list_scenarios(self, decision_id: str) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        out: list[dict[str, Any]] = []
        for row in self._finance_scenario_rows(decision_id):
            variables = list(self.session.scalars(select(ScenarioVariable).where(ScenarioVariable.scenario_id == row.id).order_by(ScenarioVariable.created_at, ScenarioVariable.id)))
            out.append(self._scenario_dict(row, variables))
        return out

    def replace_scenarios(self, decision_id: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        for row in self._finance_scenario_rows(decision_id):
            self.session.delete(row)
        self.session.flush()
        for item in items:
            name = str(item.get("name") or item.get("title") or item.get("label") or "").strip()
            if not name:
                raise ValueError("finance_scenario_name_required")
            metadata = deepcopy(item.get("metadata") or {})
            metadata["domain"] = FINANCE_DOMAIN_MARKER
            if item.get("id") not in (None, ""):
                metadata["source_id"] = str(item.get("id"))
            scenario_id = _domain_id(decision_id, "fscn", item.get("id"))
            scenario = Scenario(
                id=scenario_id,
                decision_id=decision_id,
                name=name[:300],
                description=str(item.get("description") or "") or None,
                status=str(item.get("status") or "draft")[:64],
                metadata_json=metadata,
            )
            self.session.add(scenario)
            self.session.flush()
            for variable in item.get("variables") or []:
                variable_name = str(variable.get("name") or variable.get("label") or "").strip()
                if not variable_name:
                    raise ValueError("finance_scenario_variable_name_required")
                value = variable.get("value")
                value_json = deepcopy(value) if isinstance(value, dict) else {"value": deepcopy(value)}
                value_json.setdefault("domain", FINANCE_DOMAIN_MARKER)
                self.session.add(ScenarioVariable(
                    id=_domain_id(decision_id, "fvar", f"{item.get('id') or scenario_id}:{variable.get('id') or variable_name}"),
                    scenario_id=scenario_id,
                    name=variable_name[:255],
                    value_json=value_json,
                    source_ref=None if variable.get("source_ref") is None else str(variable.get("source_ref"))[:255],
                ))
        self.session.flush()
        self._refresh_object_lists(decision_id)
        self.repository._event(decision_id, "finance.scenarios.replaced", {"count": len(items)})
        return self.list_scenarios(decision_id)

    def list_uncertainty_models(self, decision_id: str) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        return [self._uncertainty_dict(r) for r in self._finance_uncertainty_rows(decision_id)]

    def replace_uncertainty_models(self, decision_id: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        for row in self._finance_uncertainty_rows(decision_id):
            self.session.delete(row)
        self.session.flush()
        for item in items:
            model_type = str(item.get("model_type") or item.get("type") or "financial-uncertainty").strip()
            spec = deepcopy(item.get("specification") or {})
            spec["domain"] = FINANCE_DOMAIN_MARKER
            if item.get("id") not in (None, ""):
                spec["source_id"] = str(item.get("id"))
            self.session.add(UncertaintyModel(
                id=_domain_id(decision_id, "func", item.get("id")),
                decision_id=decision_id,
                model_type=model_type[:96],
                specification=spec,
                computation_ref=None if item.get("computation_ref") is None else str(item.get("computation_ref"))[:255],
                provenance_ref=None if item.get("provenance_ref") is None else str(item.get("provenance_ref"))[:255],
            ))
        self.session.flush()
        self._refresh_object_lists(decision_id)
        self.repository._event(decision_id, "finance.uncertainty_models.replaced", {"count": len(items)})
        return self.list_uncertainty_models(decision_id)

    def list_workbench_receipts(self, decision_id: str) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        return [self._receipt_dict(r) for r in self._finance_receipt_rows(decision_id)]

    def replace_workbench_receipts(self, decision_id: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        for row in self._finance_receipt_rows(decision_id):
            self.session.delete(row)
        self.session.flush()
        for item in items:
            metadata = deepcopy(item.get("metadata") or {})
            metadata.update({
                "domain": FINANCE_DOMAIN_MARKER,
                "compute_authority": "workbench",
                "receipt_only": True,
            })
            if item.get("id") not in (None, ""):
                metadata["source_id"] = str(item.get("id"))
            self.session.add(Artifact(
                id=_domain_id(decision_id, "fwbr", item.get("id")),
                decision_id=decision_id,
                artifact_type=FINANCE_RECEIPT_ARTIFACT_TYPE,
                schema_id=str(item.get("schema_id") or "scds-workbench-computation-receipt/1.0")[:255],
                uri=None if item.get("uri") is None else str(item.get("uri")),
                checksum_sha256=None if item.get("checksum_sha256") is None else str(item.get("checksum_sha256"))[:64],
                provenance_ref=None if item.get("provenance_ref") is None else str(item.get("provenance_ref"))[:255],
                metadata_json=metadata,
            ))
        self.session.flush()
        self._refresh_object_lists(decision_id)
        self.repository._event(decision_id, "finance.workbench_receipts.replaced", {"count": len(items), "compute_authority": "workbench"})
        return self.list_workbench_receipts(decision_id)

    def _refresh_object_lists(self, decision_id: str) -> None:
        obj = self._finance_object(decision_id)
        if obj is None:
            return
        payload = deepcopy(obj.payload or {})
        payload["assumptions"] = self.list_assumptions(decision_id)
        payload["scenarios"] = self.list_scenarios(decision_id)
        payload["uncertainty_models"] = self.list_uncertainty_models(decision_id)
        payload["workbench_receipts"] = self.list_workbench_receipts(decision_id)
        obj.payload = payload
        self.session.flush()

    def get_finance(self, decision_id: str) -> dict[str, Any]:
        self._require_decision(decision_id)
        obj = self._finance_object(decision_id)
        state = finance_domain_template(decision_id)
        if obj:
            state.update(deepcopy(obj.payload or {}))
        state["schema"] = FINANCE_DOMAIN_SCHEMA
        state["version"] = FINANCE_DOMAIN_VERSION
        state["decision_id"] = decision_id
        state["assumptions"] = self.list_assumptions(decision_id)
        state["scenarios"] = self.list_scenarios(decision_id)
        state["uncertainty_models"] = self.list_uncertainty_models(decision_id)
        state["workbench_receipts"] = self.list_workbench_receipts(decision_id)
        return state

    def upsert_finance(self, decision_id: str, request: FinanceStateUpsert) -> dict[str, Any]:
        self._require_decision(decision_id)
        self.repository.bind_module(
            decision_id,
            FINANCE_MODULE_ID,
            enabled=True,
            configuration={
                "domain_schema": FINANCE_DOMAIN_SCHEMA,
                "storage_authority": "python-postgresql",
                "compute_authority": "workbench",
            },
        )
        assumptions = self.replace_assumptions(decision_id, request.assumptions)
        scenarios = self.replace_scenarios(decision_id, request.scenarios)
        uncertainty_models = self.replace_uncertainty_models(decision_id, request.uncertainty_models)
        workbench_receipts = self.replace_workbench_receipts(decision_id, request.workbench_receipts)
        state = finance_domain_template(decision_id)
        state.update({
            "currency": request.currency.upper(),
            "base_year": request.base_year,
            "horizon_years": request.horizon_years,
            "capital_context": deepcopy(request.capital_context),
            "cost_context": deepcopy(request.cost_context),
            "revenue_context": deepcopy(request.revenue_context),
            "discounting_context": deepcopy(request.discounting_context),
            "model_refs": deepcopy(request.model_refs),
            "valuation_refs": deepcopy(request.valuation_refs),
            "cost_benefit_refs": deepcopy(request.cost_benefit_refs),
            "assumptions": assumptions,
            "scenarios": scenarios,
            "uncertainty_models": uncertainty_models,
            "workbench_receipts": workbench_receipts,
            "evidence_refs": deepcopy(request.evidence_refs),
            "notes": deepcopy(request.notes),
            "provenance": {**finance_domain_template(decision_id)["provenance"], **deepcopy(request.provenance)},
        })
        obj = self._finance_object(decision_id)
        if obj is None:
            obj = DecisionObject(
                id=_id("finance"),
                decision_id=decision_id,
                object_type=FINANCE_OBJECT_TYPE,
                schema_id=FINANCE_DOMAIN_SCHEMA,
                payload=state,
                provenance_ref=request.provenance_ref,
            )
            self.session.add(obj)
            event = "finance.domain.created"
        else:
            obj.schema_id = FINANCE_DOMAIN_SCHEMA
            obj.payload = state
            obj.provenance_ref = request.provenance_ref
            event = "finance.domain.updated"
        self.session.flush()
        self.repository._event(decision_id, event, {
            "schema": FINANCE_DOMAIN_SCHEMA,
            "assumptions": len(assumptions),
            "scenarios": len(scenarios),
            "uncertainty_models": len(uncertainty_models),
            "workbench_receipts": len(workbench_receipts),
            "compute_authority": "workbench",
        })
        return self.get_finance(decision_id)

    def import_legacy(self, request: FinanceLegacyImport) -> tuple[dict[str, Any], bool]:
        artifact = deepcopy(request.artifact or {})
        if not artifact:
            raise ValueError("finance_artifact_required")
        decision_id = request.decision_id or str(artifact.get("decision_id") or _id("dec"))[:64]
        decision = self.repository.get_decision(decision_id)
        created = decision is None
        if request.project_id and not self.repository.get_project(request.project_id):
            self.repository.create_project(
                project_id=request.project_id,
                title=request.project_title or "Imported Catalyst Finance",
                owner_ref=request.owner_ref,
                metadata={"source": "legacy-catalyst-finance"},
            )
        if decision is None:
            self.repository.create_decision(
                decision_id=decision_id,
                project_id=request.project_id,
                decision_question=str(artifact.get("decision_question") or artifact.get("question") or "Imported finance decision context"),
                lifecycle_state="evaluation",
                metadata={"legacy_source": "catalyst-finance"},
            )

        assumptions = deepcopy(artifact.get("assumptions") or artifact.get("financial_assumptions") or [])
        scenarios = deepcopy(artifact.get("scenarios") or artifact.get("financial_scenarios") or [])
        uncertainty = deepcopy(artifact.get("uncertainty_models") or artifact.get("uncertainty") or [])
        receipts = deepcopy(artifact.get("workbench_receipts") or artifact.get("computation_receipts") or [])
        if not receipts and artifact.get("workbench_result_ref"):
            receipts = [{"id": "legacy-workbench-result", "uri": artifact.get("workbench_result_ref"), "metadata": {"legacy": True}}]

        state = FinanceStateUpsert(
            currency=str(artifact.get("currency") or "USD"),
            base_year=artifact.get("base_year"),
            horizon_years=artifact.get("horizon_years") or artifact.get("model_years"),
            capital_context=deepcopy(artifact.get("capital_context") or artifact.get("capital") or {}),
            cost_context=deepcopy(artifact.get("cost_context") or artifact.get("costs") or {}),
            revenue_context=deepcopy(artifact.get("revenue_context") or artifact.get("revenues") or {}),
            discounting_context=deepcopy(artifact.get("discounting_context") or artifact.get("discounting") or {}),
            model_refs=deepcopy(artifact.get("model_refs") or artifact.get("models") or []),
            valuation_refs=deepcopy(artifact.get("valuation_refs") or artifact.get("valuations") or []),
            cost_benefit_refs=deepcopy(artifact.get("cost_benefit_refs") or artifact.get("cost_benefit") or []),
            assumptions=assumptions,
            scenarios=scenarios,
            uncertainty_models=uncertainty,
            workbench_receipts=receipts,
            evidence_refs=deepcopy(artifact.get("evidence_refs") or []),
            notes=deepcopy(artifact.get("notes") or []),
            provenance={
                "source": "legacy-catalyst-finance",
                "legacy_source_preserved": True,
                "legacy_artifact": artifact,
                "records": [{"type": "migration", "release": "3.6.0"}],
            },
            provenance_ref=request.provenance_ref,
        )
        result = self.upsert_finance(decision_id, state)
        self.repository._event(decision_id, "finance.legacy_imported", {"source_preserved": True, "compute_authority": "workbench"})
        return result, created
