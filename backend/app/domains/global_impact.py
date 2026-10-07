from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.persistence.models import Artifact, Claim, DecisionObject, EvidenceLink
from app.persistence.repository import PersistenceRepository

GLOBAL_IMPACT_DOMAIN_SCHEMA = "scds-global-impact-domain/1.0"
GLOBAL_IMPACT_DOMAIN_VERSION = "1.0"
GLOBAL_IMPACT_MODULE_ID = "global-impact"
GLOBAL_IMPACT_OBJECT_TYPE = "global-impact-domain"
GLOBAL_IMPACT_INDICATOR_ARTIFACT_TYPE = "global-impact-indicator"
GLOBAL_IMPACT_DOMAIN_MARKER = "global-impact"


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:24]}"


def _domain_id(decision_id: str, prefix: str, source_id: Any | None = None) -> str:
    if source_id not in (None, ""):
        raw = f"{decision_id}:{GLOBAL_IMPACT_DOMAIN_MARKER}:{prefix}:{source_id}".encode("utf-8")
        return f"{prefix}_{sha256(raw).hexdigest()[:24]}"
    return _id(prefix)


def _is_domain_metadata(value: Any) -> bool:
    return isinstance(value, dict) and value.get("domain") == GLOBAL_IMPACT_DOMAIN_MARKER


def global_impact_domain_contract() -> dict[str, Any]:
    return {
        "schema": GLOBAL_IMPACT_DOMAIN_SCHEMA,
        "version": GLOBAL_IMPACT_DOMAIN_VERSION,
        "module_id": GLOBAL_IMPACT_MODULE_ID,
        "display_name": "Global Impact Catalyst",
        "status": "python-domain-authoritative",
        "storage_authority": "python-postgresql",
        "compute_authority": "workbench",
        "kernel_contract_schema": "scds-decision-kernel/1.0",
        "repository_schema": "scds-python-decision-repository/1.0",
        "owns": [
            "impact-context",
            "impact-objectives-and-boundaries",
            "impact-stakeholders",
            "impact-pathways",
            "environmental-impact-context",
            "social-impact-context",
            "economic-impact-context",
            "sdg-alignment",
            "carbon-impact-context",
            "resource-impact-context",
            "distributional-impact-context",
            "impact-claims",
            "impact-indicators-and-targets",
            "impact-provenance",
        ],
        "shared_kernel_objects": [
            "decision", "alternative", "criterion", "evidence_ref", "assumption",
            "scenario", "artifact_ref", "provenance_ref", "outcome",
        ],
        "normalized_postgresql_tables": [
            "claims", "evidence_links", "artifacts", "decision_objects",
            "decision_module_bindings", "decision_events",
        ],
        "providers": {
            "compute_authority": "workbench",
            "evidence": ["knowledge-library", "research-librarian"],
            "spatial_and_live_context": ["site-intelligence"],
            "datasets": ["workspace", "knowledge-library"],
            "research": ["research-lab"],
        },
        "compatibility": {
            "legacy_global_impact_import": True,
            "legacy_wordpress_source_preserved": True,
            "typed_platform_artifact_adapter_preserved": True,
            "decision_packet_projection_preserved": True,
            "workbench_handoff_contract_preserved": True,
        },
        "boundaries": {
            "shared_decision_identity_owned_by_kernel": True,
            "sdg_alignment_is_not_proof_of_impact": True,
            "modeled_impact_is_not_observed_outcome": True,
            "indicator_change_is_not_causal_attribution": True,
            "distributional_judgments_remain_explicit_and_reviewable": True,
            "workbench_is_compute_authority": True,
            "decision_studio_executes_impact_models": False,
            "automatic_impact_verification": False,
            "automatic_sustainability_rating": False,
            "automatic_recommendation": False,
            "automatic_approval": False,
            "final_decision_authority": "human-governed",
        },
        "security": {
            "read_scope": "global-impact:read",
            "write_scope": "global-impact:write",
            "repository_key_also_authorized": True,
        },
    }


def global_impact_domain_template(decision_id: str = "") -> dict[str, Any]:
    return {
        "schema": GLOBAL_IMPACT_DOMAIN_SCHEMA,
        "version": GLOBAL_IMPACT_DOMAIN_VERSION,
        "decision_id": decision_id,
        "impact_context": {},
        "impact_objectives": [],
        "impact_boundaries": {},
        "stakeholders": [],
        "impact_pathways": [],
        "environmental_impacts": [],
        "social_impacts": [],
        "economic_impacts": [],
        "sdg_alignments": [],
        "carbon_context": {},
        "resource_impacts": [],
        "distributional_impacts": [],
        "impact_claims": [],
        "indicators": [],
        "evidence_links": [],
        "notes": [],
        "provenance": {
            "source": "global-impact-python-domain",
            "legacy_source_preserved": True,
            "records": [],
        },
        "authorities": {
            "storage_authority": "python-postgresql",
            "compute_authority": "workbench",
            "final_decision_authority": "human-governed",
        },
        "boundaries": {
            "sdg_alignment_is_not_proof_of_impact": True,
            "modeled_impact_is_not_observed_outcome": True,
            "indicator_change_is_not_causal_attribution": True,
            "automatic_impact_verification": False,
            "automatic_sustainability_rating": False,
            "automatic_recommendation": False,
            "automatic_approval": False,
        },
    }


class GlobalImpactStateUpsert(BaseModel):
    impact_context: dict[str, Any] = Field(default_factory=dict)
    impact_objectives: list[dict[str, Any]] = Field(default_factory=list)
    impact_boundaries: dict[str, Any] = Field(default_factory=dict)
    stakeholders: list[dict[str, Any]] = Field(default_factory=list)
    impact_pathways: list[dict[str, Any]] = Field(default_factory=list)
    environmental_impacts: list[dict[str, Any]] = Field(default_factory=list)
    social_impacts: list[dict[str, Any]] = Field(default_factory=list)
    economic_impacts: list[dict[str, Any]] = Field(default_factory=list)
    sdg_alignments: list[dict[str, Any]] = Field(default_factory=list)
    carbon_context: dict[str, Any] = Field(default_factory=dict)
    resource_impacts: list[dict[str, Any]] = Field(default_factory=list)
    distributional_impacts: list[dict[str, Any]] = Field(default_factory=list)
    impact_claims: list[dict[str, Any]] = Field(default_factory=list)
    indicators: list[dict[str, Any]] = Field(default_factory=list)
    evidence_links: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[Any] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    provenance_ref: str | None = Field(default=None, max_length=255)


class GlobalImpactClaimsReplace(BaseModel):
    impact_claims: list[dict[str, Any]] = Field(default_factory=list)


class GlobalImpactIndicatorsReplace(BaseModel):
    indicators: list[dict[str, Any]] = Field(default_factory=list)


class GlobalImpactEvidenceLinksReplace(BaseModel):
    evidence_links: list[dict[str, Any]] = Field(default_factory=list)


class GlobalImpactLegacyImport(BaseModel):
    artifact: dict[str, Any] = Field(default_factory=dict)
    decision_id: str | None = Field(default=None, max_length=64)
    project_id: str | None = Field(default=None, max_length=64)
    project_title: str | None = Field(default=None, max_length=300)
    owner_ref: str | None = Field(default=None, max_length=255)
    provenance_ref: str | None = Field(default=None, max_length=255)


class GlobalImpactDomainRepository:
    """Authoritative Global Impact state with explicit impact-evidence boundaries."""

    schema = GLOBAL_IMPACT_DOMAIN_SCHEMA
    module_id = GLOBAL_IMPACT_MODULE_ID

    def __init__(self, session: Session):
        self.session = session
        self.repository = PersistenceRepository(session)

    def _require_decision(self, decision_id: str):
        row = self.repository.get_decision(decision_id)
        if not row:
            raise LookupError("decision_not_found")
        return row

    def _domain_object(self, decision_id: str) -> DecisionObject | None:
        return self.session.scalar(select(DecisionObject).where(
            DecisionObject.decision_id == decision_id,
            DecisionObject.object_type == GLOBAL_IMPACT_OBJECT_TYPE,
        ))

    def _claim_rows(self, decision_id: str) -> list[Claim]:
        rows = list(self.session.scalars(select(Claim).where(Claim.decision_id == decision_id).order_by(Claim.created_at, Claim.id)))
        return [row for row in rows if _is_domain_metadata(row.metadata_json)]

    def _indicator_rows(self, decision_id: str) -> list[Artifact]:
        rows = list(self.session.scalars(select(Artifact).where(
            Artifact.decision_id == decision_id,
            Artifact.artifact_type == GLOBAL_IMPACT_INDICATOR_ARTIFACT_TYPE,
        ).order_by(Artifact.created_at, Artifact.id)))
        return [row for row in rows if _is_domain_metadata(row.metadata_json)]

    def _evidence_link_rows(self, decision_id: str) -> list[EvidenceLink]:
        rows = list(self.session.scalars(select(EvidenceLink).where(EvidenceLink.decision_id == decision_id).order_by(EvidenceLink.created_at, EvidenceLink.id)))
        return [row for row in rows if _is_domain_metadata(row.metadata_json)]

    @staticmethod
    def _claim_dict(row: Claim) -> dict[str, Any]:
        metadata = deepcopy(row.metadata_json or {})
        return {
            "id": row.id,
            "text": row.text,
            "epistemic_status": row.epistemic_status,
            "impact_dimension": metadata.get("impact_dimension"),
            "kind": metadata.get("kind", "impact-claim"),
            "metadata": metadata,
        }

    @staticmethod
    def _indicator_dict(row: Artifact) -> dict[str, Any]:
        metadata = deepcopy(row.metadata_json or {})
        return {
            "id": row.id,
            "label": metadata.get("label", ""),
            "indicator_type": metadata.get("indicator_type", "indicator"),
            "dimension": metadata.get("dimension"),
            "unit": metadata.get("unit"),
            "baseline": metadata.get("baseline"),
            "target": metadata.get("target"),
            "value": metadata.get("value"),
            "observed": bool(metadata.get("observed", False)),
            "observed_at": metadata.get("observed_at"),
            "source_ref": metadata.get("source_ref"),
            "uri": row.uri,
            "checksum_sha256": row.checksum_sha256,
            "provenance_ref": row.provenance_ref,
            "metadata": metadata,
        }

    @staticmethod
    def _evidence_link_dict(row: EvidenceLink) -> dict[str, Any]:
        return {
            "id": row.id,
            "claim_id": row.claim_id,
            "evidence_ref": row.evidence_ref,
            "relation": row.relation,
            "provenance_ref": row.provenance_ref,
            "metadata": deepcopy(row.metadata_json or {}),
        }

    def list_impact_claims(self, decision_id: str) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        return [self._claim_dict(row) for row in self._claim_rows(decision_id)]

    def replace_impact_claims(self, decision_id: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        domain_ids = {row.id for row in self._claim_rows(decision_id)}
        for link in self._evidence_link_rows(decision_id):
            if link.claim_id in domain_ids:
                self.session.delete(link)
        for row in self._claim_rows(decision_id):
            self.session.delete(row)
        self.session.flush()
        for item in items:
            text = str(item.get("text") or item.get("claim") or item.get("statement") or "").strip()
            if not text:
                raise ValueError("global_impact_claim_text_required")
            metadata = deepcopy(item.get("metadata") or {})
            metadata.update({
                "domain": GLOBAL_IMPACT_DOMAIN_MARKER,
                "kind": str(item.get("kind") or metadata.get("kind") or "impact-claim")[:64],
                "impact_dimension": item.get("impact_dimension") or item.get("dimension") or metadata.get("impact_dimension"),
                "impact_verified": False,
                "causal_attribution_verified": False,
            })
            if item.get("id") not in (None, ""):
                metadata["source_id"] = str(item.get("id"))
            self.session.add(Claim(
                id=_domain_id(decision_id, "gicl", item.get("id")),
                decision_id=decision_id,
                text=text,
                epistemic_status=str(item.get("epistemic_status") or item.get("status") or "unresolved")[:64],
                metadata_json=metadata,
            ))
        self.session.flush()
        self._refresh_object_lists(decision_id)
        self.repository._event(decision_id, "global_impact.claims.replaced", {"count": len(items), "automatic_impact_verification": False})
        return self.list_impact_claims(decision_id)

    def list_indicators(self, decision_id: str) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        return [self._indicator_dict(row) for row in self._indicator_rows(decision_id)]

    def replace_indicators(self, decision_id: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        for row in self._indicator_rows(decision_id):
            self.session.delete(row)
        self.session.flush()
        for item in items:
            label = str(item.get("label") or item.get("name") or item.get("indicator") or "").strip()
            if not label:
                raise ValueError("global_impact_indicator_label_required")
            observed = bool(item.get("observed", False))
            metadata = deepcopy(item.get("metadata") or {})
            metadata.update({
                "domain": GLOBAL_IMPACT_DOMAIN_MARKER,
                "label": label,
                "indicator_type": str(item.get("indicator_type") or item.get("type") or "indicator")[:96],
                "dimension": item.get("dimension"),
                "unit": item.get("unit"),
                "baseline": item.get("baseline"),
                "target": item.get("target"),
                "value": item.get("value"),
                "observed": observed,
                "observed_at": item.get("observed_at"),
                "source_ref": item.get("source_ref"),
                "causal_attribution_verified": False,
                "modeled_impact_is_observed_outcome": False,
            })
            if item.get("id") not in (None, ""):
                metadata["source_id"] = str(item.get("id"))
            self.session.add(Artifact(
                id=_domain_id(decision_id, "giin", item.get("id")),
                decision_id=decision_id,
                artifact_type=GLOBAL_IMPACT_INDICATOR_ARTIFACT_TYPE,
                schema_id=str(item.get("schema_id") or "scds-global-impact-indicator/1.0")[:255],
                uri=None if item.get("uri") is None else str(item.get("uri")),
                checksum_sha256=None if item.get("checksum_sha256") is None else str(item.get("checksum_sha256"))[:64],
                provenance_ref=None if item.get("provenance_ref") is None else str(item.get("provenance_ref"))[:255],
                metadata_json=metadata,
            ))
        self.session.flush()
        self._refresh_object_lists(decision_id)
        self.repository._event(decision_id, "global_impact.indicators.replaced", {"count": len(items), "automatic_causal_attribution": False})
        return self.list_indicators(decision_id)

    def _resolve_claim_id(self, decision_id: str, value: Any | None) -> str | None:
        if value in (None, ""):
            return None
        raw = str(value)
        direct = self.session.get(Claim, raw)
        if direct and direct.decision_id == decision_id and _is_domain_metadata(direct.metadata_json):
            return direct.id
        for row in self._claim_rows(decision_id):
            if str((row.metadata_json or {}).get("source_id") or "") == raw:
                return row.id
        raise ValueError("global_impact_claim_not_found")

    def list_evidence_links(self, decision_id: str) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        return [self._evidence_link_dict(row) for row in self._evidence_link_rows(decision_id)]

    def replace_evidence_links(self, decision_id: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        for row in self._evidence_link_rows(decision_id):
            self.session.delete(row)
        self.session.flush()
        for item in items:
            evidence_ref = str(item.get("evidence_ref") or item.get("evidence") or "").strip()
            if not evidence_ref:
                raise ValueError("global_impact_evidence_ref_required")
            metadata = deepcopy(item.get("metadata") or {})
            metadata.update({
                "domain": GLOBAL_IMPACT_DOMAIN_MARKER,
                "impact_verified": False,
                "causal_attribution_verified": False,
            })
            if item.get("id") not in (None, ""):
                metadata["source_id"] = str(item.get("id"))
            self.session.add(EvidenceLink(
                id=_domain_id(decision_id, "giel", item.get("id")),
                decision_id=decision_id,
                claim_id=self._resolve_claim_id(decision_id, item.get("claim_id") or item.get("claim_ref")),
                evidence_ref=evidence_ref[:255],
                relation=str(item.get("relation") or "context")[:64],
                provenance_ref=None if item.get("provenance_ref") is None else str(item.get("provenance_ref"))[:255],
                metadata_json=metadata,
            ))
        self.session.flush()
        self._refresh_object_lists(decision_id)
        self.repository._event(decision_id, "global_impact.evidence_links.replaced", {"count": len(items), "automatic_impact_verification": False})
        return self.list_evidence_links(decision_id)

    def _refresh_object_lists(self, decision_id: str) -> None:
        obj = self._domain_object(decision_id)
        if obj is None:
            return
        payload = deepcopy(obj.payload or {})
        payload["impact_claims"] = self.list_impact_claims(decision_id)
        payload["indicators"] = self.list_indicators(decision_id)
        payload["evidence_links"] = self.list_evidence_links(decision_id)
        obj.payload = payload
        self.session.flush()

    def get_global_impact(self, decision_id: str) -> dict[str, Any]:
        self._require_decision(decision_id)
        obj = self._domain_object(decision_id)
        state = global_impact_domain_template(decision_id)
        if obj:
            state.update(deepcopy(obj.payload or {}))
        state["schema"] = GLOBAL_IMPACT_DOMAIN_SCHEMA
        state["version"] = GLOBAL_IMPACT_DOMAIN_VERSION
        state["decision_id"] = decision_id
        state["impact_claims"] = self.list_impact_claims(decision_id)
        state["indicators"] = self.list_indicators(decision_id)
        state["evidence_links"] = self.list_evidence_links(decision_id)
        return state

    def upsert_global_impact(self, decision_id: str, request: GlobalImpactStateUpsert) -> dict[str, Any]:
        self._require_decision(decision_id)
        self.repository.bind_module(
            decision_id,
            GLOBAL_IMPACT_MODULE_ID,
            enabled=True,
            configuration={
                "domain_schema": GLOBAL_IMPACT_DOMAIN_SCHEMA,
                "storage_authority": "python-postgresql",
                "compute_authority": "workbench",
                "impact_boundary": "evidence-linked-human-review",
            },
        )
        claims = self.replace_impact_claims(decision_id, request.impact_claims)
        indicators = self.replace_indicators(decision_id, request.indicators)
        evidence_links = self.replace_evidence_links(decision_id, request.evidence_links)
        state = global_impact_domain_template(decision_id)
        state.update({
            "impact_context": deepcopy(request.impact_context),
            "impact_objectives": deepcopy(request.impact_objectives),
            "impact_boundaries": deepcopy(request.impact_boundaries),
            "stakeholders": deepcopy(request.stakeholders),
            "impact_pathways": deepcopy(request.impact_pathways),
            "environmental_impacts": deepcopy(request.environmental_impacts),
            "social_impacts": deepcopy(request.social_impacts),
            "economic_impacts": deepcopy(request.economic_impacts),
            "sdg_alignments": deepcopy(request.sdg_alignments),
            "carbon_context": deepcopy(request.carbon_context),
            "resource_impacts": deepcopy(request.resource_impacts),
            "distributional_impacts": deepcopy(request.distributional_impacts),
            "impact_claims": claims,
            "indicators": indicators,
            "evidence_links": evidence_links,
            "notes": deepcopy(request.notes),
            "provenance": {**global_impact_domain_template(decision_id)["provenance"], **deepcopy(request.provenance)},
        })
        obj = self._domain_object(decision_id)
        if obj is None:
            obj = DecisionObject(
                id=_id("gimpact"),
                decision_id=decision_id,
                object_type=GLOBAL_IMPACT_OBJECT_TYPE,
                schema_id=GLOBAL_IMPACT_DOMAIN_SCHEMA,
                payload=state,
                provenance_ref=request.provenance_ref,
            )
            self.session.add(obj)
            event = "global_impact.domain.created"
        else:
            obj.schema_id = GLOBAL_IMPACT_DOMAIN_SCHEMA
            obj.payload = state
            obj.provenance_ref = request.provenance_ref
            event = "global_impact.domain.updated"
        self.session.flush()
        self.repository._event(decision_id, event, {
            "schema": GLOBAL_IMPACT_DOMAIN_SCHEMA,
            "impact_claims": len(claims),
            "indicators": len(indicators),
            "evidence_links": len(evidence_links),
            "automatic_impact_verification": False,
            "automatic_sustainability_rating": False,
        })
        return self.get_global_impact(decision_id)

    def import_legacy(self, request: GlobalImpactLegacyImport) -> tuple[dict[str, Any], bool]:
        artifact = deepcopy(request.artifact or {})
        if not artifact:
            raise ValueError("global_impact_artifact_required")
        decision_id = request.decision_id or str(artifact.get("decision_id") or _id("dec"))[:64]
        decision = self.repository.get_decision(decision_id)
        created = decision is None
        if request.project_id and not self.repository.get_project(request.project_id):
            self.repository.create_project(
                project_id=request.project_id,
                title=request.project_title or "Imported Global Impact Catalyst",
                owner_ref=request.owner_ref,
                metadata={"source": "legacy-global-impact"},
            )
        if decision is None:
            self.repository.create_decision(
                decision_id=decision_id,
                project_id=request.project_id,
                decision_question=str(artifact.get("decision_question") or artifact.get("question") or "Imported global-impact decision context"),
                lifecycle_state="evaluation",
                metadata={"legacy_source": "global-impact"},
            )
        state = GlobalImpactStateUpsert(
            impact_context=deepcopy(artifact.get("impact_context") or artifact.get("context") or {}),
            impact_objectives=deepcopy(artifact.get("impact_objectives") or artifact.get("objectives") or []),
            impact_boundaries=deepcopy(artifact.get("impact_boundaries") or artifact.get("boundaries") or {}),
            stakeholders=deepcopy(artifact.get("impact_stakeholders") or artifact.get("stakeholders") or artifact.get("beneficiaries") or []),
            impact_pathways=deepcopy(artifact.get("impact_pathways") or artifact.get("pathways") or artifact.get("theory_of_change") or []),
            environmental_impacts=deepcopy(artifact.get("environmental_impacts") or artifact.get("environmental_impact") or []),
            social_impacts=deepcopy(artifact.get("social_impacts") or artifact.get("social_impact") or []),
            economic_impacts=deepcopy(artifact.get("economic_impacts") or artifact.get("economic_impact") or []),
            sdg_alignments=deepcopy(artifact.get("sdg_alignments") or artifact.get("sdg_alignment") or artifact.get("sdgs") or []),
            carbon_context=deepcopy(artifact.get("carbon_context") or artifact.get("carbon_impact") or {}),
            resource_impacts=deepcopy(artifact.get("resource_impacts") or artifact.get("resource_impact") or []),
            distributional_impacts=deepcopy(artifact.get("distributional_impacts") or artifact.get("distributional_impact") or []),
            impact_claims=deepcopy(artifact.get("impact_claims") or artifact.get("claims") or []),
            indicators=deepcopy(artifact.get("indicators") or artifact.get("impact_indicators") or artifact.get("metrics") or []),
            evidence_links=deepcopy(artifact.get("evidence_links") or artifact.get("evidence_relationships") or []),
            notes=deepcopy(artifact.get("notes") or []),
            provenance={
                "source": "legacy-global-impact",
                "legacy_source_preserved": True,
                "legacy_artifact": artifact,
                "records": [{"type": "migration", "release": "3.8.0"}],
            },
            provenance_ref=request.provenance_ref,
        )
        result = self.upsert_global_impact(decision_id, state)
        self.repository._event(decision_id, "global_impact.legacy_imported", {"source_preserved": True})
        return result, created
