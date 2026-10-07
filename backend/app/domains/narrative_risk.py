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

NARRATIVE_RISK_DOMAIN_SCHEMA = "scds-narrative-risk-domain/1.0"
NARRATIVE_RISK_DOMAIN_VERSION = "1.0"
NARRATIVE_RISK_MODULE_ID = "narrative-risk"
NARRATIVE_RISK_OBJECT_TYPE = "narrative-risk-domain"
NARRATIVE_RISK_SIGNAL_ARTIFACT_TYPE = "narrative-risk-signal"
NARRATIVE_RISK_DOMAIN_MARKER = "narrative-risk"


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:24]}"


def _domain_id(decision_id: str, prefix: str, source_id: Any | None = None) -> str:
    if source_id not in (None, ""):
        raw = f"{decision_id}:{NARRATIVE_RISK_DOMAIN_MARKER}:{prefix}:{source_id}".encode("utf-8")
        return f"{prefix}_{sha256(raw).hexdigest()[:24]}"
    return _id(prefix)


def _is_domain_metadata(value: Any) -> bool:
    return isinstance(value, dict) and value.get("domain") == NARRATIVE_RISK_DOMAIN_MARKER


def narrative_risk_domain_contract() -> dict[str, Any]:
    return {
        "schema": NARRATIVE_RISK_DOMAIN_SCHEMA,
        "version": NARRATIVE_RISK_DOMAIN_VERSION,
        "module_id": NARRATIVE_RISK_MODULE_ID,
        "display_name": "Narrative Risk",
        "status": "python-domain-authoritative",
        "storage_authority": "python-postgresql",
        "kernel_contract_schema": "scds-decision-kernel/1.0",
        "repository_schema": "scds-python-decision-repository/1.0",
        "owns": [
            "risk-context",
            "claims-and-risk-hypotheses",
            "signals-and-indicators",
            "actors-and-stakeholders",
            "exposures-and-impacts",
            "competing-narratives",
            "evidence-relationships",
            "watch-conditions",
            "mitigation-context",
            "risk-provenance",
        ],
        "shared_kernel_objects": [
            "decision", "evidence_ref", "assumption", "scenario", "challenge",
            "artifact_ref", "provenance_ref", "outcome",
        ],
        "normalized_postgresql_tables": [
            "claims", "evidence_links", "artifacts", "decision_objects",
            "decision_module_bindings", "decision_events",
        ],
        "providers": {
            "evidence": ["knowledge-library", "research-librarian"],
            "graph_and_entity_context": ["platform-core"],
            "live_context": ["site-intelligence"],
            "research": ["research-lab"],
        },
        "compatibility": {
            "legacy_narrative_risk_import": True,
            "legacy_wordpress_source_preserved": True,
            "typed_platform_artifact_adapter_preserved": True,
            "decision_packet_projection_preserved": True,
        },
        "boundaries": {
            "shared_decision_identity_owned_by_kernel": True,
            "claim_is_not_fact_without_evidence": True,
            "signal_is_not_causality": True,
            "narrative_is_not_truth_verification": True,
            "risk_likelihood_preserves_uncertainty": True,
            "automatic_truth_verification": False,
            "automatic_causality_inference": False,
            "automatic_recommendation": False,
            "automatic_escalation_or_action": False,
            "final_decision_authority": "human-governed",
        },
        "security": {
            "read_scope": "narrative-risk:read",
            "write_scope": "narrative-risk:write",
            "repository_key_also_authorized": True,
        },
    }


def narrative_risk_domain_template(decision_id: str = "") -> dict[str, Any]:
    return {
        "schema": NARRATIVE_RISK_DOMAIN_SCHEMA,
        "version": NARRATIVE_RISK_DOMAIN_VERSION,
        "decision_id": decision_id,
        "risk_context": {},
        "actors": [],
        "exposures": [],
        "narratives": [],
        "mitigations": [],
        "watch_conditions": [],
        "claims": [],
        "signals": [],
        "evidence_links": [],
        "notes": [],
        "provenance": {
            "source": "narrative-risk-python-domain",
            "legacy_source_preserved": True,
            "records": [],
        },
        "authorities": {
            "storage_authority": "python-postgresql",
            "final_decision_authority": "human-governed",
        },
        "boundaries": {
            "automatic_truth_verification": False,
            "automatic_causality_inference": False,
            "automatic_recommendation": False,
            "automatic_escalation_or_action": False,
        },
    }


class NarrativeRiskStateUpsert(BaseModel):
    risk_context: dict[str, Any] = Field(default_factory=dict)
    actors: list[dict[str, Any]] = Field(default_factory=list)
    exposures: list[dict[str, Any]] = Field(default_factory=list)
    narratives: list[dict[str, Any]] = Field(default_factory=list)
    mitigations: list[dict[str, Any]] = Field(default_factory=list)
    watch_conditions: list[dict[str, Any]] = Field(default_factory=list)
    claims: list[dict[str, Any]] = Field(default_factory=list)
    signals: list[dict[str, Any]] = Field(default_factory=list)
    evidence_links: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[Any] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    provenance_ref: str | None = Field(default=None, max_length=255)


class NarrativeRiskClaimsReplace(BaseModel):
    claims: list[dict[str, Any]] = Field(default_factory=list)


class NarrativeRiskSignalsReplace(BaseModel):
    signals: list[dict[str, Any]] = Field(default_factory=list)


class NarrativeRiskEvidenceLinksReplace(BaseModel):
    evidence_links: list[dict[str, Any]] = Field(default_factory=list)


class NarrativeRiskLegacyImport(BaseModel):
    artifact: dict[str, Any] = Field(default_factory=dict)
    decision_id: str | None = Field(default=None, max_length=64)
    project_id: str | None = Field(default=None, max_length=64)
    project_title: str | None = Field(default=None, max_length=300)
    owner_ref: str | None = Field(default=None, max_length=255)
    provenance_ref: str | None = Field(default=None, max_length=255)


class NarrativeRiskDomainRepository:
    """Authoritative Narrative Risk state with explicit epistemic boundaries."""

    schema = NARRATIVE_RISK_DOMAIN_SCHEMA
    module_id = NARRATIVE_RISK_MODULE_ID

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
            DecisionObject.object_type == NARRATIVE_RISK_OBJECT_TYPE,
        ))

    def _claim_rows(self, decision_id: str) -> list[Claim]:
        rows = list(self.session.scalars(select(Claim).where(Claim.decision_id == decision_id).order_by(Claim.created_at, Claim.id)))
        return [row for row in rows if _is_domain_metadata(row.metadata_json)]

    def _signal_rows(self, decision_id: str) -> list[Artifact]:
        rows = list(self.session.scalars(select(Artifact).where(
            Artifact.decision_id == decision_id,
            Artifact.artifact_type == NARRATIVE_RISK_SIGNAL_ARTIFACT_TYPE,
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
            "kind": metadata.get("kind", "claim"),
            "metadata": metadata,
        }

    @staticmethod
    def _signal_dict(row: Artifact) -> dict[str, Any]:
        metadata = deepcopy(row.metadata_json or {})
        return {
            "id": row.id,
            "signal_type": metadata.get("signal_type", "signal"),
            "label": metadata.get("label", ""),
            "observed_at": metadata.get("observed_at"),
            "severity": metadata.get("severity"),
            "direction": metadata.get("direction"),
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

    def list_claims(self, decision_id: str) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        return [self._claim_dict(row) for row in self._claim_rows(decision_id)]

    def replace_claims(self, decision_id: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
                raise ValueError("narrative_risk_claim_text_required")
            metadata = deepcopy(item.get("metadata") or {})
            metadata.update({
                "domain": NARRATIVE_RISK_DOMAIN_MARKER,
                "kind": str(item.get("kind") or metadata.get("kind") or "claim")[:64],
                "truth_verified": False,
            })
            if item.get("id") not in (None, ""):
                metadata["source_id"] = str(item.get("id"))
            self.session.add(Claim(
                id=_domain_id(decision_id, "nrcl", item.get("id")),
                decision_id=decision_id,
                text=text,
                epistemic_status=str(item.get("epistemic_status") or item.get("status") or "unresolved")[:64],
                metadata_json=metadata,
            ))
        self.session.flush()
        self._refresh_object_lists(decision_id)
        self.repository._event(decision_id, "narrative_risk.claims.replaced", {"count": len(items), "automatic_truth_verification": False})
        return self.list_claims(decision_id)

    def list_signals(self, decision_id: str) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        return [self._signal_dict(row) for row in self._signal_rows(decision_id)]

    def replace_signals(self, decision_id: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        for row in self._signal_rows(decision_id):
            self.session.delete(row)
        self.session.flush()
        for item in items:
            label = str(item.get("label") or item.get("name") or item.get("signal") or "").strip()
            if not label:
                raise ValueError("narrative_risk_signal_label_required")
            metadata = deepcopy(item.get("metadata") or {})
            metadata.update({
                "domain": NARRATIVE_RISK_DOMAIN_MARKER,
                "label": label,
                "signal_type": str(item.get("signal_type") or item.get("type") or "signal")[:96],
                "observed_at": item.get("observed_at"),
                "severity": item.get("severity"),
                "direction": item.get("direction"),
                "source_ref": item.get("source_ref"),
                "causality_inferred": False,
            })
            if item.get("id") not in (None, ""):
                metadata["source_id"] = str(item.get("id"))
            self.session.add(Artifact(
                id=_domain_id(decision_id, "nrsg", item.get("id")),
                decision_id=decision_id,
                artifact_type=NARRATIVE_RISK_SIGNAL_ARTIFACT_TYPE,
                schema_id=str(item.get("schema_id") or "scds-narrative-risk-signal/1.0")[:255],
                uri=None if item.get("uri") is None else str(item.get("uri")),
                checksum_sha256=None if item.get("checksum_sha256") is None else str(item.get("checksum_sha256"))[:64],
                provenance_ref=None if item.get("provenance_ref") is None else str(item.get("provenance_ref"))[:255],
                metadata_json=metadata,
            ))
        self.session.flush()
        self._refresh_object_lists(decision_id)
        self.repository._event(decision_id, "narrative_risk.signals.replaced", {"count": len(items), "automatic_causality_inference": False})
        return self.list_signals(decision_id)

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
        raise ValueError("narrative_risk_claim_not_found")

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
                raise ValueError("narrative_risk_evidence_ref_required")
            metadata = deepcopy(item.get("metadata") or {})
            metadata.update({
                "domain": NARRATIVE_RISK_DOMAIN_MARKER,
                "truth_verified": False,
                "causality_inferred": False,
            })
            if item.get("id") not in (None, ""):
                metadata["source_id"] = str(item.get("id"))
            self.session.add(EvidenceLink(
                id=_domain_id(decision_id, "nrel", item.get("id")),
                decision_id=decision_id,
                claim_id=self._resolve_claim_id(decision_id, item.get("claim_id") or item.get("claim_ref")),
                evidence_ref=evidence_ref[:255],
                relation=str(item.get("relation") or "context")[:64],
                provenance_ref=None if item.get("provenance_ref") is None else str(item.get("provenance_ref"))[:255],
                metadata_json=metadata,
            ))
        self.session.flush()
        self._refresh_object_lists(decision_id)
        self.repository._event(decision_id, "narrative_risk.evidence_links.replaced", {"count": len(items), "automatic_truth_verification": False})
        return self.list_evidence_links(decision_id)

    def _refresh_object_lists(self, decision_id: str) -> None:
        obj = self._domain_object(decision_id)
        if obj is None:
            return
        payload = deepcopy(obj.payload or {})
        payload["claims"] = self.list_claims(decision_id)
        payload["signals"] = self.list_signals(decision_id)
        payload["evidence_links"] = self.list_evidence_links(decision_id)
        obj.payload = payload
        self.session.flush()

    def get_narrative_risk(self, decision_id: str) -> dict[str, Any]:
        self._require_decision(decision_id)
        obj = self._domain_object(decision_id)
        state = narrative_risk_domain_template(decision_id)
        if obj:
            state.update(deepcopy(obj.payload or {}))
        state["schema"] = NARRATIVE_RISK_DOMAIN_SCHEMA
        state["version"] = NARRATIVE_RISK_DOMAIN_VERSION
        state["decision_id"] = decision_id
        state["claims"] = self.list_claims(decision_id)
        state["signals"] = self.list_signals(decision_id)
        state["evidence_links"] = self.list_evidence_links(decision_id)
        return state

    def upsert_narrative_risk(self, decision_id: str, request: NarrativeRiskStateUpsert) -> dict[str, Any]:
        self._require_decision(decision_id)
        self.repository.bind_module(
            decision_id,
            NARRATIVE_RISK_MODULE_ID,
            enabled=True,
            configuration={
                "domain_schema": NARRATIVE_RISK_DOMAIN_SCHEMA,
                "storage_authority": "python-postgresql",
                "epistemic_boundary": "evidence-linked-human-review",
            },
        )
        claims = self.replace_claims(decision_id, request.claims)
        signals = self.replace_signals(decision_id, request.signals)
        evidence_links = self.replace_evidence_links(decision_id, request.evidence_links)
        state = narrative_risk_domain_template(decision_id)
        state.update({
            "risk_context": deepcopy(request.risk_context),
            "actors": deepcopy(request.actors),
            "exposures": deepcopy(request.exposures),
            "narratives": deepcopy(request.narratives),
            "mitigations": deepcopy(request.mitigations),
            "watch_conditions": deepcopy(request.watch_conditions),
            "claims": claims,
            "signals": signals,
            "evidence_links": evidence_links,
            "notes": deepcopy(request.notes),
            "provenance": {**narrative_risk_domain_template(decision_id)["provenance"], **deepcopy(request.provenance)},
        })
        obj = self._domain_object(decision_id)
        if obj is None:
            obj = DecisionObject(
                id=_id("narrisk"),
                decision_id=decision_id,
                object_type=NARRATIVE_RISK_OBJECT_TYPE,
                schema_id=NARRATIVE_RISK_DOMAIN_SCHEMA,
                payload=state,
                provenance_ref=request.provenance_ref,
            )
            self.session.add(obj)
            event = "narrative_risk.domain.created"
        else:
            obj.schema_id = NARRATIVE_RISK_DOMAIN_SCHEMA
            obj.payload = state
            obj.provenance_ref = request.provenance_ref
            event = "narrative_risk.domain.updated"
        self.session.flush()
        self.repository._event(decision_id, event, {
            "schema": NARRATIVE_RISK_DOMAIN_SCHEMA,
            "claims": len(claims),
            "signals": len(signals),
            "evidence_links": len(evidence_links),
            "automatic_truth_verification": False,
            "automatic_causality_inference": False,
        })
        return self.get_narrative_risk(decision_id)

    def import_legacy(self, request: NarrativeRiskLegacyImport) -> tuple[dict[str, Any], bool]:
        artifact = deepcopy(request.artifact or {})
        if not artifact:
            raise ValueError("narrative_risk_artifact_required")
        decision_id = request.decision_id or str(artifact.get("decision_id") or _id("dec"))[:64]
        decision = self.repository.get_decision(decision_id)
        created = decision is None
        if request.project_id and not self.repository.get_project(request.project_id):
            self.repository.create_project(
                project_id=request.project_id,
                title=request.project_title or "Imported Narrative Risk",
                owner_ref=request.owner_ref,
                metadata={"source": "legacy-narrative-risk"},
            )
        if decision is None:
            self.repository.create_decision(
                decision_id=decision_id,
                project_id=request.project_id,
                decision_question=str(artifact.get("decision_question") or artifact.get("question") or "Imported narrative-risk decision context"),
                lifecycle_state="evaluation",
                metadata={"legacy_source": "narrative-risk"},
            )
        state = NarrativeRiskStateUpsert(
            risk_context=deepcopy(artifact.get("risk_context") or artifact.get("context") or {}),
            actors=deepcopy(artifact.get("actors") or artifact.get("stakeholders") or []),
            exposures=deepcopy(artifact.get("exposures") or artifact.get("impacts") or []),
            narratives=deepcopy(artifact.get("narratives") or artifact.get("competing_narratives") or []),
            mitigations=deepcopy(artifact.get("mitigations") or []),
            watch_conditions=deepcopy(artifact.get("watch_conditions") or artifact.get("watchlist") or []),
            claims=deepcopy(artifact.get("claims") or artifact.get("risk_claims") or artifact.get("hypotheses") or []),
            signals=deepcopy(artifact.get("signals") or artifact.get("indicators") or []),
            evidence_links=deepcopy(artifact.get("evidence_links") or artifact.get("evidence_relationships") or []),
            notes=deepcopy(artifact.get("notes") or []),
            provenance={
                "source": "legacy-narrative-risk",
                "legacy_source_preserved": True,
                "legacy_artifact": artifact,
                "records": [{"type": "migration", "release": "3.7.0"}],
            },
            provenance_ref=request.provenance_ref,
        )
        result = self.upsert_narrative_risk(decision_id, state)
        self.repository._event(decision_id, "narrative_risk.legacy_imported", {"source_preserved": True})
        return result, created
