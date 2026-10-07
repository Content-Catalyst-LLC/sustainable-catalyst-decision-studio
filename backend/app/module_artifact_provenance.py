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

from app.persistence.models import Artifact
from app.persistence.repository import PersistenceRepository

MODULE_ARTIFACT_SCHEMA = "scds-module-artifact/1.0"
MODULE_PROVENANCE_SCHEMA = "scds-module-provenance/1.0"
MODULE_ARTIFACT_VERSION = "1.0"
CANONICAL_MODULE_IDS = ("canvas", "finance", "narrative-risk", "global-impact")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(raw).hexdigest()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:24]}"


def module_artifact_contract() -> dict[str, Any]:
    return {
        "schema": MODULE_ARTIFACT_SCHEMA,
        "version": MODULE_ARTIFACT_VERSION,
        "provenance_schema": MODULE_PROVENANCE_SCHEMA,
        "role": "canonical-module-artifact-and-provenance-standard",
        "canonical_modules": list(CANONICAL_MODULE_IDS),
        "storage_authority": "python-postgresql",
        "module_artifact_provenance_authority": "decision-studio-kernel",
        "evidence_identity_and_source_provenance_authority": "platform-core",
        "final_decision_authority": "human-governed",
        "principles": {
            "module_ownership_is_explicit": True,
            "artifact_revisions_are_immutable": True,
            "logical_artifact_identity_is_stable_across_revisions": True,
            "every_revision_has_sha256_integrity": True,
            "parent_artifacts_are_explicit": True,
            "source_and_evidence_references_are_preserved": True,
            "external_computation_receipts_are_references_not_recomputed": True,
            "provenance_does_not_imply_truth": True,
            "provenance_does_not_imply_causality": True,
            "artifact_presence_does_not_imply_recommendation": True,
            "artifact_presence_does_not_imply_approval": True,
        },
        "compute_authorities": {"finance": "workbench", "global-impact": "workbench"},
        "persistence": {
            "table": "artifacts",
            "event_table": "decision_events",
            "schema_migration_required": False,
            "payload_storage": "artifacts.metadata_json",
            "checksum_storage": "artifacts.checksum_sha256",
        },
        "security": {
            "read_scope": "artifacts:read",
            "write_scope": "artifacts:write",
            "repository_key_also_authorized": True,
        },
    }


def module_artifact_template(decision_id: str = "", module_id: str = "canvas") -> dict[str, Any]:
    return {
        "schema": MODULE_ARTIFACT_SCHEMA,
        "version": MODULE_ARTIFACT_VERSION,
        "artifact_id": "",
        "revision_id": "",
        "revision_no": 1,
        "decision_id": decision_id,
        "module_id": module_id,
        "artifact_type": "module-output",
        "title": "",
        "status": "draft",
        "uri": None,
        "payload": {},
        "source_refs": [],
        "evidence_refs": [],
        "computation_refs": [],
        "parent_artifact_ids": [],
        "provenance": {
            "schema": MODULE_PROVENANCE_SCHEMA,
            "created_at": "",
            "actor_ref": None,
            "source_system": "decision-studio",
            "source_version": "",
            "transformation_history": [],
            "notes": [],
        },
        "ownership": {
            "module_id": module_id,
            "storage_authority": "python-postgresql",
            "final_decision_authority": "human-governed",
        },
        "integrity": {"algorithm": "sha256", "content_sha256": ""},
    }


class ModuleArtifactCreateRequest(BaseModel):
    module_id: str = Field(min_length=1, max_length=64)
    artifact_type: str = Field(min_length=1, max_length=96)
    title: str = Field(default="", max_length=300)
    status: str = Field(default="draft", max_length=64)
    uri: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    source_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    computation_refs: list[str] = Field(default_factory=list)
    parent_artifact_ids: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    provenance_ref: str | None = Field(default=None, max_length=255)
    actor_ref: str | None = Field(default=None, max_length=255)
    logical_artifact_id: str | None = Field(default=None, max_length=64)


class ModuleArtifactRevisionRequest(BaseModel):
    module_id: str = Field(min_length=1, max_length=64)
    artifact_type: str | None = Field(default=None, max_length=96)
    title: str | None = Field(default=None, max_length=300)
    status: str | None = Field(default=None, max_length=64)
    uri: str | None = None
    payload: dict[str, Any] | None = None
    source_refs: list[str] | None = None
    evidence_refs: list[str] | None = None
    computation_refs: list[str] | None = None
    parent_artifact_ids: list[str] | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    provenance_ref: str | None = Field(default=None, max_length=255)
    actor_ref: str | None = Field(default=None, max_length=255)


class ModuleArtifactValidateRequest(BaseModel):
    artifact: dict[str, Any] = Field(default_factory=dict)
    strict: bool = True


def _normalized_refs(values: list[Any] | None) -> list[str]:
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


def validate_module_artifact(document: dict[str, Any], strict: bool = True) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if document.get("schema") != MODULE_ARTIFACT_SCHEMA:
        errors.append("schema_mismatch")
    module_id = str(document.get("module_id") or "").strip().lower()
    if module_id not in CANONICAL_MODULE_IDS:
        errors.append("unknown_module")
    if not str(document.get("artifact_id") or "").strip():
        errors.append("artifact_id_required")
    if strict and not str(document.get("revision_id") or "").strip():
        errors.append("revision_id_required")
    try:
        revision_no = int(document.get("revision_no") or 0)
    except (TypeError, ValueError):
        revision_no = 0
    if revision_no < 1:
        errors.append("revision_no_must_be_positive")
    if not str(document.get("artifact_type") or "").strip():
        errors.append("artifact_type_required")
    ownership = document.get("ownership") or {}
    if strict and ownership.get("module_id") != module_id:
        errors.append("ownership_module_mismatch")
    provenance = document.get("provenance") or {}
    if provenance.get("schema") not in {None, MODULE_PROVENANCE_SCHEMA}:
        errors.append("provenance_schema_mismatch")
    if provenance.get("truth_verified") is True or provenance.get("causality_verified") is True:
        errors.append("forbidden_epistemic_claim")
    integrity = document.get("integrity") or {}
    supplied = str(integrity.get("content_sha256") or "").strip()
    calculated = _hash(_without_integrity(document))
    if supplied and supplied != calculated:
        errors.append("integrity_mismatch")
    if not supplied:
        warnings.append("integrity_hash_missing")
    return {
        "ok": not errors,
        "schema": MODULE_ARTIFACT_SCHEMA,
        "provenance_schema": MODULE_PROVENANCE_SCHEMA,
        "errors": errors,
        "warnings": warnings,
        "calculated_sha256": calculated,
    }


class ModuleArtifactRepository:
    def __init__(self, session: Session, *, app_version: str):
        self.session = session
        self.repository = PersistenceRepository(session)
        self.app_version = app_version

    def _require_decision(self, decision_id: str):
        decision = self.repository.get_decision(decision_id)
        if not decision:
            raise LookupError("decision_not_found")
        return decision

    def _rows(self, decision_id: str) -> list[Artifact]:
        return list(self.session.scalars(
            select(Artifact).where(
                Artifact.decision_id == decision_id,
                Artifact.schema_id == MODULE_ARTIFACT_SCHEMA,
            ).order_by(Artifact.created_at.asc(), Artifact.id.asc())
        ))

    @staticmethod
    def _doc(row: Artifact) -> dict[str, Any]:
        doc = deepcopy(row.metadata_json or {})
        doc.setdefault("revision_id", row.id)
        doc.setdefault("decision_id", row.decision_id)
        doc.setdefault("artifact_type", row.artifact_type)
        doc.setdefault("uri", row.uri)
        doc.setdefault("provenance_ref", row.provenance_ref)
        doc.setdefault("integrity", {"algorithm": "sha256", "content_sha256": row.checksum_sha256 or ""})
        return doc

    def list(self, decision_id: str, module_id: str | None = None, *, current_only: bool = True) -> list[dict[str, Any]]:
        self._require_decision(decision_id)
        docs = [self._doc(row) for row in self._rows(decision_id)]
        if module_id:
            docs = [doc for doc in docs if doc.get("module_id") == module_id]
        if current_only:
            latest: dict[str, dict[str, Any]] = {}
            for doc in docs:
                aid = str(doc.get("artifact_id"))
                if aid not in latest or int(doc.get("revision_no") or 0) > int(latest[aid].get("revision_no") or 0):
                    latest[aid] = doc
            docs = list(latest.values())
        return sorted(docs, key=lambda x: (str(x.get("module_id")), str(x.get("artifact_id")), int(x.get("revision_no") or 0)))

    def _resolve(self, decision_id: str, artifact_id: str) -> tuple[Artifact, dict[str, Any]]:
        self._require_decision(decision_id)
        direct = self.session.get(Artifact, artifact_id)
        if direct and direct.decision_id == decision_id and direct.schema_id == MODULE_ARTIFACT_SCHEMA:
            return direct, self._doc(direct)
        matches = [(row, self._doc(row)) for row in self._rows(decision_id) if (row.metadata_json or {}).get("artifact_id") == artifact_id]
        if not matches:
            raise LookupError("module_artifact_not_found")
        return max(matches, key=lambda item: int(item[1].get("revision_no") or 0))

    def get(self, decision_id: str, artifact_id: str) -> dict[str, Any]:
        return self._resolve(decision_id, artifact_id)[1]

    def _assert_parent_refs(self, decision_id: str, parent_ids: list[str]) -> None:
        for parent in parent_ids:
            self._resolve(decision_id, parent)

    def create(self, decision_id: str, req: ModuleArtifactCreateRequest) -> dict[str, Any]:
        self._require_decision(decision_id)
        module_id = req.module_id.strip().lower()
        if module_id not in CANONICAL_MODULE_IDS:
            raise ValueError("unknown_module")
        logical_id = (req.logical_artifact_id or _id("ma")).strip()
        if any((row.metadata_json or {}).get("artifact_id") == logical_id for row in self._rows(decision_id)):
            raise ValueError("logical_artifact_id_exists")
        parents = _normalized_refs(req.parent_artifact_ids)
        self._assert_parent_refs(decision_id, parents)
        return self._insert_revision(decision_id, logical_id, 1, req.model_dump(), previous=None, parents=parents)

    def revise(self, decision_id: str, artifact_id: str, req: ModuleArtifactRevisionRequest) -> dict[str, Any]:
        _, current = self._resolve(decision_id, artifact_id)
        logical_id = str(current["artifact_id"])
        module_id = req.module_id.strip().lower()
        if module_id != current.get("module_id"):
            raise ValueError("module_ownership_change_prohibited")
        if module_id not in CANONICAL_MODULE_IDS:
            raise ValueError("unknown_module")
        parents = _normalized_refs(req.parent_artifact_ids) if req.parent_artifact_ids is not None else [str(current["revision_id"])]
        if str(current["revision_id"]) not in parents:
            parents.insert(0, str(current["revision_id"]))
        self._assert_parent_refs(decision_id, parents)
        payload = req.model_dump()
        return self._insert_revision(decision_id, logical_id, int(current.get("revision_no") or 0) + 1, payload, previous=current, parents=parents)

    def _insert_revision(self, decision_id: str, logical_id: str, revision_no: int, raw: dict[str, Any], *, previous: dict[str, Any] | None, parents: list[str]) -> dict[str, Any]:
        revision_id = _id("mart")
        module_id = str(raw.get("module_id") or (previous or {}).get("module_id") or "").strip().lower()
        artifact_type = str(raw.get("artifact_type") or (previous or {}).get("artifact_type") or "module-output").strip()
        title = raw.get("title") if raw.get("title") is not None else (previous or {}).get("title", "")
        status = raw.get("status") if raw.get("status") is not None else (previous or {}).get("status", "draft")
        uri = raw.get("uri") if raw.get("uri") is not None else (previous or {}).get("uri")
        payload = deepcopy(raw.get("payload") if raw.get("payload") is not None else (previous or {}).get("payload", {}))
        source_refs = _normalized_refs(raw.get("source_refs") if raw.get("source_refs") is not None else (previous or {}).get("source_refs", []))
        evidence_refs = _normalized_refs(raw.get("evidence_refs") if raw.get("evidence_refs") is not None else (previous or {}).get("evidence_refs", []))
        computation_refs = _normalized_refs(raw.get("computation_refs") if raw.get("computation_refs") is not None else (previous or {}).get("computation_refs", []))
        created_at = _now()
        prior_prov = deepcopy((previous or {}).get("provenance") or {})
        supplied_prov = deepcopy(raw.get("provenance") or {})
        transformation_history = list(prior_prov.get("transformation_history") or [])
        transformation_history.extend(list(supplied_prov.get("transformation_history") or []))
        transformation_history.append({
            "at": created_at,
            "action": "artifact-created" if revision_no == 1 else "artifact-revised",
            "product": "decision-studio",
            "version": self.app_version,
            "module_id": module_id,
            "revision_no": revision_no,
        })
        provenance = {
            "schema": MODULE_PROVENANCE_SCHEMA,
            "created_at": created_at,
            "actor_ref": raw.get("actor_ref") or supplied_prov.get("actor_ref"),
            "source_system": supplied_prov.get("source_system") or prior_prov.get("source_system") or "decision-studio",
            "source_version": supplied_prov.get("source_version") or prior_prov.get("source_version") or self.app_version,
            "methodology": supplied_prov.get("methodology") or prior_prov.get("methodology"),
            "transformation_history": transformation_history,
            "notes": deepcopy(supplied_prov.get("notes") or prior_prov.get("notes") or []),
            "truth_verified": False,
            "causality_verified": False,
        }
        doc = {
            "schema": MODULE_ARTIFACT_SCHEMA,
            "version": MODULE_ARTIFACT_VERSION,
            "artifact_id": logical_id,
            "revision_id": revision_id,
            "revision_no": revision_no,
            "decision_id": decision_id,
            "module_id": module_id,
            "artifact_type": artifact_type,
            "title": str(title or ""),
            "status": str(status or "draft"),
            "uri": uri,
            "payload": payload,
            "source_refs": source_refs,
            "evidence_refs": evidence_refs,
            "computation_refs": computation_refs,
            "parent_artifact_ids": parents,
            "provenance": provenance,
            "provenance_ref": raw.get("provenance_ref") or (previous or {}).get("provenance_ref"),
            "ownership": {
                "module_id": module_id,
                "storage_authority": "python-postgresql",
                "compute_authority": "workbench" if module_id in {"finance", "global-impact"} else None,
                "final_decision_authority": "human-governed",
            },
        }
        digest = _hash(doc)
        doc["integrity"] = {"algorithm": "sha256", "content_sha256": digest}
        validation = validate_module_artifact(doc, strict=True)
        if not validation["ok"]:
            raise ValueError("invalid_module_artifact:" + ",".join(validation["errors"]))
        row = Artifact(
            id=revision_id,
            decision_id=decision_id,
            artifact_type=artifact_type,
            schema_id=MODULE_ARTIFACT_SCHEMA,
            uri=uri,
            checksum_sha256=digest,
            provenance_ref=doc.get("provenance_ref"),
            metadata_json=doc,
        )
        self.session.add(row)
        self.session.flush()
        self.repository._event(decision_id, "module_artifact.created" if revision_no == 1 else "module_artifact.revised", {
            "artifact_id": logical_id,
            "revision_id": revision_id,
            "revision_no": revision_no,
            "module_id": module_id,
            "artifact_type": artifact_type,
            "checksum_sha256": digest,
            "parent_artifact_ids": parents,
            "provenance_schema": MODULE_PROVENANCE_SCHEMA,
        }, actor_ref=raw.get("actor_ref"))
        return doc

    def lineage(self, decision_id: str, artifact_id: str) -> dict[str, Any]:
        _, current = self._resolve(decision_id, artifact_id)
        logical_id = str(current["artifact_id"])
        revisions = [self._doc(row) for row in self._rows(decision_id) if (row.metadata_json or {}).get("artifact_id") == logical_id]
        revisions.sort(key=lambda doc: int(doc.get("revision_no") or 0))
        edges: list[dict[str, str]] = []
        known = {str(doc.get("revision_id")) for doc in revisions}
        for doc in revisions:
            for parent in doc.get("parent_artifact_ids") or []:
                edges.append({
                    "from": str(parent),
                    "to": str(doc.get("revision_id")),
                    "relationship": "derived-from" if str(parent) not in known else "revision-of",
                })
        return {
            "schema": MODULE_PROVENANCE_SCHEMA,
            "artifact_id": logical_id,
            "decision_id": decision_id,
            "module_id": current.get("module_id"),
            "revision_count": len(revisions),
            "current_revision_id": current.get("revision_id"),
            "current_revision_no": current.get("revision_no"),
            "revisions": revisions,
            "edges": edges,
            "boundaries": {
                "lineage_implies_truth": False,
                "lineage_implies_causality": False,
                "lineage_implies_recommendation": False,
                "final_decision_authority": "human-governed",
            },
        }
