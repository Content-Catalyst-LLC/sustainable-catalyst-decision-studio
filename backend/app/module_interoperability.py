from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.persistence.models import DecisionObject, EvidenceLink
from app.persistence.repository import PersistenceRepository

MODULE_INTEROPERABILITY_SCHEMA = "scds-module-interoperability/1.0"
SHARED_EVIDENCE_SCHEMA = "scds-shared-evidence-reference/1.0"
MODULE_INTEROPERABILITY_VERSION = "1.0"
INTEROPERABILITY_OBJECT_TYPE = "module-interoperability-shared-evidence"
CANONICAL_MODULE_IDS = ("canvas", "finance", "narrative-risk", "global-impact")
ALLOWED_RELATIONS = {"supports", "refutes", "contextualizes", "qualifies", "illustrates", "informs", "uncertain"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:24]}"


def _hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(raw).hexdigest()


def module_interoperability_contract() -> dict[str, Any]:
    return {
        "schema": MODULE_INTEROPERABILITY_SCHEMA,
        "version": MODULE_INTEROPERABILITY_VERSION,
        "shared_evidence_schema": SHARED_EVIDENCE_SCHEMA,
        "role": "cross-module-interoperability-and-shared-evidence",
        "canonical_modules": list(CANONICAL_MODULE_IDS),
        "storage_authority": "python-postgresql",
        "evidence_identity_and_source_provenance_authority": "platform-core",
        "sharing_and_usage_authority": "decision-studio-kernel",
        "final_decision_authority": "human-governed",
        "principles": {
            "evidence_identity_is_shared_by_reference": True,
            "evidence_payload_is_not_duplicated": True,
            "owner_module_is_preserved": True,
            "consumer_modules_are_explicit": True,
            "module_specific_relations_are_preserved": True,
            "source_provenance_is_preserved_by_reference": True,
            "cross_module_usage_is_a_relationship_not_ownership_transfer": True,
            "contradictions_are_visible_not_silently_reconciled": True,
            "contradiction_annotations_are_explicit": True,
            "shared_evidence_does_not_imply_shared_interpretation": True,
            "evidence_reuse_does_not_imply_truth": True,
            "evidence_reuse_does_not_imply_causality": True,
            "evidence_reuse_does_not_imply_recommendation": True,
        },
        "persistence": {
            "document_table": "decision_objects",
            "document_object_type": INTEROPERABILITY_OBJECT_TYPE,
            "usage_edge_table": "evidence_links",
            "schema_migration_required": False,
        },
        "security": {
            "read_scope": "interoperability:read",
            "write_scope": "interoperability:write",
            "repository_key_also_authorized": True,
        },
    }


def module_interoperability_template(decision_id: str = "") -> dict[str, Any]:
    return {
        "schema": MODULE_INTEROPERABILITY_SCHEMA,
        "version": MODULE_INTEROPERABILITY_VERSION,
        "decision_id": decision_id,
        "shared_evidence": [],
        "contradiction_annotations": [],
        "artifact_links": [],
        "provenance": {
            "created_at": "",
            "updated_at": "",
            "actor_ref": None,
            "source_system": "decision-studio",
            "notes": [],
        },
        "boundaries": {
            "evidence_payload_duplicated": False,
            "ownership_transfer_on_share": False,
            "shared_evidence_implies_shared_interpretation": False,
            "contradiction_is_automatically_resolved": False,
            "truth_is_automatically_verified": False,
            "causality_is_automatically_inferred": False,
            "recommendation_is_automatic": False,
            "final_decision_authority": "human-governed",
        },
        "integrity": {"algorithm": "sha256", "content_sha256": ""},
    }


class SharedEvidenceUsage(BaseModel):
    module_id: str = Field(min_length=1, max_length=64)
    relation: str = Field(default="informs", max_length=64)
    purpose: str = Field(default="", max_length=600)
    claim_ref: str | None = Field(default=None, max_length=255)
    provenance_ref: str | None = Field(default=None, max_length=255)
    notes: list[str] = Field(default_factory=list)


class SharedEvidenceReference(BaseModel):
    evidence_ref: str = Field(min_length=1, max_length=255)
    owner_module: str = Field(min_length=1, max_length=64)
    source_ref: str | None = Field(default=None, max_length=255)
    source_provenance_ref: str | None = Field(default=None, max_length=255)
    artifact_ref: str | None = Field(default=None, max_length=255)
    usages: list[SharedEvidenceUsage] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ContradictionAnnotation(BaseModel):
    annotation_id: str | None = Field(default=None, max_length=64)
    evidence_refs: list[str] = Field(default_factory=list)
    module_ids: list[str] = Field(default_factory=list)
    statement: str = Field(min_length=1, max_length=4000)
    status: str = Field(default="open", max_length=64)
    provenance_ref: str | None = Field(default=None, max_length=255)
    notes: list[str] = Field(default_factory=list)


class ArtifactLink(BaseModel):
    artifact_ref: str = Field(min_length=1, max_length=255)
    owner_module: str = Field(min_length=1, max_length=64)
    consumer_modules: list[str] = Field(default_factory=list)
    relationship: str = Field(default="references", max_length=64)


class ModuleInteroperabilityUpsertRequest(BaseModel):
    shared_evidence: list[SharedEvidenceReference] = Field(default_factory=list)
    contradiction_annotations: list[ContradictionAnnotation] = Field(default_factory=list)
    artifact_links: list[ArtifactLink] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    actor_ref: str | None = Field(default=None, max_length=255)


class SharedEvidenceShareRequest(BaseModel):
    evidence_ref: str = Field(min_length=1, max_length=255)
    owner_module: str = Field(min_length=1, max_length=64)
    source_ref: str | None = Field(default=None, max_length=255)
    source_provenance_ref: str | None = Field(default=None, max_length=255)
    artifact_ref: str | None = Field(default=None, max_length=255)
    usage: SharedEvidenceUsage
    actor_ref: str | None = Field(default=None, max_length=255)


class ModuleInteroperabilityValidateRequest(BaseModel):
    interoperability: dict[str, Any] = Field(default_factory=dict)
    strict: bool = True


def _module(value: Any) -> str:
    return str(value or "").strip().lower()


def _dedupe_strings(values: list[Any] | None) -> list[str]:
    out: list[str] = []
    for value in values or []:
        item = str(value or "").strip()
        if item and item not in out:
            out.append(item)
    return out


def _without_integrity(document: dict[str, Any]) -> dict[str, Any]:
    copy = deepcopy(document)
    copy.pop("integrity", None)
    return copy


def validate_module_interoperability(document: dict[str, Any], strict: bool = True) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if document.get("schema") != MODULE_INTEROPERABILITY_SCHEMA:
        errors.append("schema_mismatch")
    seen_evidence: set[str] = set()
    for item in document.get("shared_evidence") or []:
        ref = str(item.get("evidence_ref") or "").strip()
        owner = _module(item.get("owner_module"))
        if not ref:
            errors.append("evidence_ref_required")
            continue
        if ref in seen_evidence:
            errors.append(f"duplicate_evidence_ref:{ref}")
        seen_evidence.add(ref)
        if owner not in CANONICAL_MODULE_IDS:
            errors.append(f"unknown_owner_module:{owner or 'missing'}")
        for usage in item.get("usages") or []:
            consumer = _module(usage.get("module_id"))
            relation = str(usage.get("relation") or "informs").strip().lower()
            if consumer not in CANONICAL_MODULE_IDS:
                errors.append(f"unknown_consumer_module:{consumer or 'missing'}")
            if relation not in ALLOWED_RELATIONS:
                errors.append(f"unsupported_evidence_relation:{relation}")
    for ann in document.get("contradiction_annotations") or []:
        refs = _dedupe_strings(ann.get("evidence_refs"))
        modules = [_module(x) for x in ann.get("module_ids") or []]
        if strict and len(refs) < 1:
            errors.append("contradiction_evidence_ref_required")
        if strict and len(set(modules)) < 2:
            errors.append("contradiction_requires_two_modules")
        for mid in modules:
            if mid not in CANONICAL_MODULE_IDS:
                errors.append(f"unknown_contradiction_module:{mid or 'missing'}")
        for ref in refs:
            if ref not in seen_evidence:
                warnings.append(f"contradiction_ref_not_in_shared_evidence:{ref}")
    for link in document.get("artifact_links") or []:
        if _module(link.get("owner_module")) not in CANONICAL_MODULE_IDS:
            errors.append("unknown_artifact_owner_module")
        for mid in link.get("consumer_modules") or []:
            if _module(mid) not in CANONICAL_MODULE_IDS:
                errors.append(f"unknown_artifact_consumer_module:{mid}")
    boundaries = document.get("boundaries") or {}
    forbidden_true = [
        "evidence_payload_duplicated", "ownership_transfer_on_share",
        "shared_evidence_implies_shared_interpretation", "contradiction_is_automatically_resolved",
        "truth_is_automatically_verified", "causality_is_automatically_inferred", "recommendation_is_automatic",
    ]
    for key in forbidden_true:
        if boundaries.get(key) is True:
            errors.append(f"forbidden_boundary:{key}")
    integrity = document.get("integrity") or {}
    supplied = str(integrity.get("content_sha256") or "").strip()
    calculated = _hash(_without_integrity(document))
    if supplied and supplied != calculated:
        errors.append("integrity_mismatch")
    if strict and not supplied:
        warnings.append("integrity_hash_missing")
    return {
        "ok": not errors,
        "schema": MODULE_INTEROPERABILITY_SCHEMA,
        "shared_evidence_schema": SHARED_EVIDENCE_SCHEMA,
        "errors": errors,
        "warnings": warnings,
        "calculated_sha256": calculated,
    }


class ModuleInteroperabilityRepository:
    def __init__(self, session: Session, *, app_version: str):
        self.session = session
        self.repository = PersistenceRepository(session)
        self.app_version = app_version

    def _require_decision(self, decision_id: str):
        decision = self.repository.get_decision(decision_id)
        if not decision:
            raise LookupError("decision_not_found")
        return decision

    def _row(self, decision_id: str) -> DecisionObject | None:
        rows = list(self.session.scalars(select(DecisionObject).where(
            DecisionObject.decision_id == decision_id,
            DecisionObject.object_type == INTEROPERABILITY_OBJECT_TYPE,
        ).order_by(DecisionObject.updated_at.desc())))
        return rows[0] if rows else None

    def get(self, decision_id: str) -> dict[str, Any]:
        self._require_decision(decision_id)
        row = self._row(decision_id)
        if not row:
            return module_interoperability_template(decision_id)
        return deepcopy(row.payload or {})

    def _normalize(self, decision_id: str, req: ModuleInteroperabilityUpsertRequest, previous: dict[str, Any] | None = None) -> dict[str, Any]:
        prior = previous or {}
        now = _now()
        shared: list[dict[str, Any]] = []
        for item in req.shared_evidence:
            owner = _module(item.owner_module)
            usages: list[dict[str, Any]] = []
            seen_usage: set[tuple[str, str, str | None, str]] = set()
            for usage in item.usages:
                mid = _module(usage.module_id)
                relation = usage.relation.strip().lower() or "informs"
                key = (mid, relation, usage.claim_ref, usage.purpose)
                if key in seen_usage:
                    continue
                seen_usage.add(key)
                usages.append({
                    "usage_id": _id("seu"),
                    "module_id": mid,
                    "relation": relation,
                    "purpose": usage.purpose,
                    "claim_ref": usage.claim_ref,
                    "provenance_ref": usage.provenance_ref,
                    "notes": list(usage.notes),
                })
            shared.append({
                "schema": SHARED_EVIDENCE_SCHEMA,
                "evidence_ref": item.evidence_ref.strip(),
                "owner_module": owner,
                "consumer_modules": sorted({u["module_id"] for u in usages}),
                "source_ref": item.source_ref,
                "source_provenance_ref": item.source_provenance_ref,
                "artifact_ref": item.artifact_ref,
                "usages": usages,
                "tags": _dedupe_strings(item.tags),
            })
        annotations: list[dict[str, Any]] = []
        for ann in req.contradiction_annotations:
            annotations.append({
                "annotation_id": ann.annotation_id or _id("contra"),
                "evidence_refs": _dedupe_strings(ann.evidence_refs),
                "module_ids": sorted({_module(x) for x in ann.module_ids}),
                "statement": ann.statement,
                "status": ann.status,
                "provenance_ref": ann.provenance_ref,
                "notes": list(ann.notes),
            })
        artifact_links = [{
            "artifact_ref": link.artifact_ref,
            "owner_module": _module(link.owner_module),
            "consumer_modules": sorted({_module(x) for x in link.consumer_modules}),
            "relationship": link.relationship,
        } for link in req.artifact_links]
        created = (prior.get("provenance") or {}).get("created_at") or now
        document = {
            "schema": MODULE_INTEROPERABILITY_SCHEMA,
            "version": MODULE_INTEROPERABILITY_VERSION,
            "decision_id": decision_id,
            "shared_evidence": sorted(shared, key=lambda x: x["evidence_ref"]),
            "contradiction_annotations": annotations,
            "artifact_links": artifact_links,
            "provenance": {
                "created_at": created,
                "updated_at": now,
                "actor_ref": req.actor_ref or (req.provenance or {}).get("actor_ref"),
                "source_system": (req.provenance or {}).get("source_system") or "decision-studio",
                "source_version": self.app_version,
                "notes": list((req.provenance or {}).get("notes") or []),
            },
            "boundaries": module_interoperability_template(decision_id)["boundaries"],
        }
        document["integrity"] = {"algorithm": "sha256", "content_sha256": _hash(document)}
        validation = validate_module_interoperability(document, strict=True)
        if not validation["ok"]:
            raise ValueError("invalid_module_interoperability:" + ",".join(validation["errors"]))
        return document

    def _replace_usage_edges(self, decision_id: str, document: dict[str, Any]) -> None:
        existing = list(self.session.scalars(select(EvidenceLink).where(EvidenceLink.decision_id == decision_id)))
        for row in existing:
            if (row.metadata_json or {}).get("domain") == "module-interoperability":
                self.session.delete(row)
        self.session.flush()
        for item in document.get("shared_evidence") or []:
            for usage in item.get("usages") or []:
                row = EvidenceLink(
                    id=_id("sevl"),
                    decision_id=decision_id,
                    claim_id=None,
                    evidence_ref=item["evidence_ref"],
                    relation=usage["relation"],
                    provenance_ref=usage.get("provenance_ref") or item.get("source_provenance_ref"),
                    metadata_json={
                        "schema": SHARED_EVIDENCE_SCHEMA,
                        "domain": "module-interoperability",
                        "owner_module": item["owner_module"],
                        "consumer_module": usage["module_id"],
                        "usage_id": usage["usage_id"],
                        "purpose": usage.get("purpose", ""),
                        "claim_ref": usage.get("claim_ref"),
                        "source_ref": item.get("source_ref"),
                        "artifact_ref": item.get("artifact_ref"),
                        "ownership_transfer": False,
                    },
                )
                self.session.add(row)
        self.session.flush()

    def upsert(self, decision_id: str, req: ModuleInteroperabilityUpsertRequest) -> dict[str, Any]:
        self._require_decision(decision_id)
        existing = self._row(decision_id)
        previous = deepcopy(existing.payload or {}) if existing else None
        document = self._normalize(decision_id, req, previous=previous)
        if existing:
            existing.schema_id = MODULE_INTEROPERABILITY_SCHEMA
            existing.payload = document
            existing.provenance_ref = (document.get("provenance") or {}).get("actor_ref")
        else:
            existing = DecisionObject(
                id=f"interop_{decision_id}"[:64],
                decision_id=decision_id,
                object_type=INTEROPERABILITY_OBJECT_TYPE,
                schema_id=MODULE_INTEROPERABILITY_SCHEMA,
                payload=document,
                provenance_ref=(document.get("provenance") or {}).get("actor_ref"),
            )
            self.session.add(existing)
        self._replace_usage_edges(decision_id, document)
        self.repository._event(decision_id, "module_interoperability.updated", {
            "schema": MODULE_INTEROPERABILITY_SCHEMA,
            "shared_evidence_count": len(document["shared_evidence"]),
            "usage_count": sum(len(x.get("usages") or []) for x in document["shared_evidence"]),
            "contradiction_annotation_count": len(document["contradiction_annotations"]),
            "artifact_link_count": len(document["artifact_links"]),
            "checksum_sha256": document["integrity"]["content_sha256"],
        }, actor_ref=req.actor_ref)
        return document

    def share(self, decision_id: str, req: SharedEvidenceShareRequest) -> dict[str, Any]:
        current = self.get(decision_id)
        items: list[SharedEvidenceReference] = []
        matched = False
        for item in current.get("shared_evidence") or []:
            if item.get("evidence_ref") == req.evidence_ref:
                if _module(item.get("owner_module")) != _module(req.owner_module):
                    raise ValueError("evidence_owner_change_prohibited")
                usages = [SharedEvidenceUsage(**{k: v for k, v in u.items() if k in SharedEvidenceUsage.model_fields}) for u in item.get("usages") or []]
                usages.append(req.usage)
                items.append(SharedEvidenceReference(
                    evidence_ref=req.evidence_ref,
                    owner_module=req.owner_module,
                    source_ref=req.source_ref or item.get("source_ref"),
                    source_provenance_ref=req.source_provenance_ref or item.get("source_provenance_ref"),
                    artifact_ref=req.artifact_ref or item.get("artifact_ref"),
                    usages=usages,
                    tags=item.get("tags") or [],
                ))
                matched = True
            else:
                items.append(SharedEvidenceReference(**{k: v for k, v in item.items() if k in SharedEvidenceReference.model_fields}))
        if not matched:
            items.append(SharedEvidenceReference(
                evidence_ref=req.evidence_ref,
                owner_module=req.owner_module,
                source_ref=req.source_ref,
                source_provenance_ref=req.source_provenance_ref,
                artifact_ref=req.artifact_ref,
                usages=[req.usage],
            ))
        annotations = [ContradictionAnnotation(**a) for a in current.get("contradiction_annotations") or []]
        artifacts = [ArtifactLink(**a) for a in current.get("artifact_links") or []]
        return self.upsert(decision_id, ModuleInteroperabilityUpsertRequest(
            shared_evidence=items,
            contradiction_annotations=annotations,
            artifact_links=artifacts,
            provenance={"notes": ["shared-evidence-edge-added"]},
            actor_ref=req.actor_ref,
        ))

    def evidence(self, decision_id: str, evidence_ref: str) -> dict[str, Any]:
        document = self.get(decision_id)
        for item in document.get("shared_evidence") or []:
            if item.get("evidence_ref") == evidence_ref:
                links = []
                for row in self.session.scalars(select(EvidenceLink).where(
                    EvidenceLink.decision_id == decision_id,
                    EvidenceLink.evidence_ref == evidence_ref,
                )):
                    if (row.metadata_json or {}).get("domain") == "module-interoperability":
                        links.append({
                            "link_id": row.id,
                            "relation": row.relation,
                            "provenance_ref": row.provenance_ref,
                            "metadata": deepcopy(row.metadata_json or {}),
                        })
                return {"shared_evidence": deepcopy(item), "usage_edges": links}
        raise LookupError("shared_evidence_not_found")

    def diagnostics(self, decision_id: str) -> dict[str, Any]:
        document = self.get(decision_id)
        shared = document.get("shared_evidence") or []
        explicit_contradictions = document.get("contradiction_annotations") or []
        relation_disagreements: list[dict[str, Any]] = []
        polarity = {"supports": 1, "refutes": -1}
        for item in shared:
            grouped: dict[str, list[dict[str, Any]]] = {}
            for usage in item.get("usages") or []:
                claim_ref = str(usage.get("claim_ref") or "")
                if claim_ref:
                    grouped.setdefault(claim_ref, []).append(usage)
            for claim_ref, usages in grouped.items():
                signs = {polarity[u["relation"]] for u in usages if u.get("relation") in polarity}
                if signs == {-1, 1}:
                    relation_disagreements.append({
                        "evidence_ref": item.get("evidence_ref"),
                        "claim_ref": claim_ref,
                        "modules": sorted({u.get("module_id") for u in usages}),
                        "relations": sorted({u.get("relation") for u in usages}),
                        "interpretation": "relationship-disagreement-not-truth-adjudication",
                    })
        return {
            "schema": MODULE_INTEROPERABILITY_SCHEMA,
            "decision_id": decision_id,
            "shared_evidence_count": len(shared),
            "cross_module_evidence_count": sum(1 for x in shared if len(set(x.get("consumer_modules") or [])) > 1),
            "explicit_contradiction_count": len(explicit_contradictions),
            "relation_disagreement_count": len(relation_disagreements),
            "explicit_contradictions": deepcopy(explicit_contradictions),
            "relation_disagreements": relation_disagreements,
            "boundaries": {
                "relation_disagreement_is_not_truth_adjudication": True,
                "contradiction_is_not_automatically_resolved": True,
                "evidence_reuse_does_not_imply_causality": True,
                "final_decision_authority": "human-governed",
            },
        }
