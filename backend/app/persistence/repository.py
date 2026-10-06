from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .contracts import REPOSITORY_AUTHORITY, REPOSITORY_SCHEMA
from .models import (
    Decision,
    DecisionEvent,
    DecisionModule,
    DecisionModuleBinding,
    DecisionObject,
    DecisionProject,
    Snapshot,
)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:24]}"


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _project_dict(row: DecisionProject) -> dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title,
        "status": row.status,
        "owner_ref": row.owner_ref,
        "metadata": row.metadata_json,
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
    }


def _decision_dict(row: Decision) -> dict[str, Any]:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "decision_question": row.decision_question,
        "lifecycle_state": row.lifecycle_state,
        "final_decision_authority": row.final_decision_authority,
        "current_snapshot_id": row.current_snapshot_id,
        "metadata": row.metadata_json,
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
    }


def _object_dict(row: DecisionObject) -> dict[str, Any]:
    return {
        "id": row.id,
        "decision_id": row.decision_id,
        "object_type": row.object_type,
        "schema_id": row.schema_id,
        "payload": row.payload,
        "provenance_ref": row.provenance_ref,
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
    }


def _snapshot_dict(row: Snapshot) -> dict[str, Any]:
    return {
        "id": row.id,
        "decision_id": row.decision_id,
        "snapshot_type": row.snapshot_type,
        "payload": row.payload,
        "provenance_ref": row.provenance_ref,
        "created_at": _iso(row.created_at),
    }


class PersistenceRepository:
    """Authoritative Python/PostgreSQL Decision Studio repository (v3.4)."""

    authority = REPOSITORY_AUTHORITY
    schema = REPOSITORY_SCHEMA

    def __init__(self, session: Session):
        self.session = session

    def _event(self, decision_id: str, event_type: str, payload: dict[str, Any] | None = None, actor_ref: str | None = None) -> None:
        max_seq = self.session.scalar(
            select(func.max(DecisionEvent.sequence_no)).where(DecisionEvent.decision_id == decision_id)
        )
        self.session.add(
            DecisionEvent(
                id=_id("evt"),
                decision_id=decision_id,
                event_type=event_type,
                actor_ref=actor_ref,
                event_payload=payload or {},
                sequence_no=(max_seq or 0) + 1,
            )
        )

    def get_project(self, project_id: str) -> DecisionProject | None:
        return self.session.get(DecisionProject, project_id)

    def create_project(self, *, project_id: str | None, title: str, status: str = "active", owner_ref: str | None = None, metadata: dict[str, Any] | None = None) -> DecisionProject:
        pid = project_id or _id("proj")
        existing = self.get_project(pid)
        if existing:
            existing.title = title
            existing.status = status
            existing.owner_ref = owner_ref
            existing.metadata_json = metadata or {}
            self.session.flush()
            return existing
        row = DecisionProject(id=pid, title=title, status=status, owner_ref=owner_ref, metadata_json=metadata or {})
        self.session.add(row)
        self.session.flush()
        return row

    def get_decision(self, decision_id: str) -> Decision | None:
        return self.session.get(Decision, decision_id)

    def create_decision(self, *, decision_id: str | None, project_id: str | None, decision_question: str, lifecycle_state: str = "framing", metadata: dict[str, Any] | None = None) -> Decision:
        did = decision_id or _id("dec")
        if self.get_decision(did):
            raise ValueError("decision_exists")
        if project_id and not self.get_project(project_id):
            raise LookupError("project_not_found")
        row = Decision(
            id=did,
            project_id=project_id,
            decision_question=decision_question,
            lifecycle_state=lifecycle_state,
            final_decision_authority="human-governed",
            metadata_json=metadata or {},
        )
        self.session.add(row)
        self.session.flush()
        self._event(did, "decision.created", {"repository_schema": self.schema})
        return row

    def list_decisions(self, project_id: str | None = None) -> list[Decision]:
        stmt = select(Decision).order_by(Decision.created_at.desc())
        if project_id:
            stmt = stmt.where(Decision.project_id == project_id)
        return list(self.session.scalars(stmt))

    def update_decision(self, decision_id: str, patch: dict[str, Any]) -> Decision | None:
        row = self.get_decision(decision_id)
        if not row:
            return None
        if "project_id" in patch:
            project_id = patch["project_id"]
            if project_id and not self.get_project(project_id):
                raise LookupError("project_not_found")
            row.project_id = project_id
        if patch.get("decision_question") is not None:
            row.decision_question = patch["decision_question"]
        if patch.get("lifecycle_state") is not None:
            row.lifecycle_state = patch["lifecycle_state"]
        if patch.get("metadata") is not None:
            row.metadata_json = patch["metadata"]
        self.session.flush()
        self._event(decision_id, "decision.updated", {"fields": sorted(patch)})
        return row

    def upsert_unified_decision_object(self, decision_id: str, *, payload: dict[str, Any], schema_id: str = "scds-decision-object/1.0", object_id: str | None = None, provenance_ref: str | None = None) -> DecisionObject:
        if not self.get_decision(decision_id):
            raise LookupError("decision_not_found")
        stmt = select(DecisionObject).where(
            DecisionObject.decision_id == decision_id,
            DecisionObject.object_type == "unified-decision-object",
        )
        row = self.session.scalar(stmt)
        if row is None:
            oid = object_id or f"obj_{sha256(decision_id.encode('utf-8')).hexdigest()[:24]}"
            row = DecisionObject(
                id=oid,
                decision_id=decision_id,
                object_type="unified-decision-object",
                schema_id=schema_id,
                payload=payload,
                provenance_ref=provenance_ref,
            )
            self.session.add(row)
            event_type = "decision_object.created"
        else:
            row.schema_id = schema_id
            row.payload = payload
            row.provenance_ref = provenance_ref
            event_type = "decision_object.updated"
        self.session.flush()
        self._event(decision_id, event_type, {"object_id": row.id, "schema_id": schema_id})
        return row

    def get_unified_decision_object(self, decision_id: str) -> DecisionObject | None:
        return self.session.scalar(
            select(DecisionObject).where(
                DecisionObject.decision_id == decision_id,
                DecisionObject.object_type == "unified-decision-object",
            )
        )

    def bind_module(self, decision_id: str, module_id: str, *, enabled: bool = True, configuration: dict[str, Any] | None = None) -> DecisionModuleBinding:
        if not self.get_decision(decision_id):
            raise LookupError("decision_not_found")
        if not self.session.get(DecisionModule, module_id):
            raise LookupError("module_not_found")
        row = self.session.scalar(
            select(DecisionModuleBinding).where(
                DecisionModuleBinding.decision_id == decision_id,
                DecisionModuleBinding.module_id == module_id,
            )
        )
        if row is None:
            row = DecisionModuleBinding(
                id=_id("bind"),
                decision_id=decision_id,
                module_id=module_id,
                enabled=enabled,
                configuration=configuration or {},
            )
            self.session.add(row)
        else:
            row.enabled = enabled
            row.configuration = configuration or {}
        self.session.flush()
        self._event(decision_id, "decision_module.bound", {"module_id": module_id, "enabled": enabled})
        return row

    def create_snapshot(self, decision_id: str, *, payload: dict[str, Any], snapshot_type: str = "decision", snapshot_id: str | None = None, provenance_ref: str | None = None) -> Snapshot:
        decision = self.get_decision(decision_id)
        if not decision:
            raise LookupError("decision_not_found")
        row = Snapshot(
            id=snapshot_id or _id("snap"),
            decision_id=decision_id,
            snapshot_type=snapshot_type,
            payload=payload,
            provenance_ref=provenance_ref,
        )
        self.session.add(row)
        self.session.flush()
        decision.current_snapshot_id = row.id
        self._event(decision_id, "decision_snapshot.created", {"snapshot_id": row.id, "snapshot_type": snapshot_type})
        return row

    def current_snapshot(self, decision_id: str) -> Snapshot | None:
        decision = self.get_decision(decision_id)
        if not decision or not decision.current_snapshot_id:
            return None
        return self.session.get(Snapshot, decision.current_snapshot_id)

    def import_decision_object(self, decision_object: dict[str, Any], *, project_id: str | None = None, project_title: str | None = None, owner_ref: str | None = None, provenance_ref: str | None = None) -> tuple[Decision, DecisionObject, bool]:
        did = str(decision_object.get("decision_id") or "").strip() or _id("dec")
        question = str(decision_object.get("question") or "Imported Decision Studio decision").strip()
        lifecycle_state = str(decision_object.get("status") or "framing")
        if project_id and not self.get_project(project_id):
            self.create_project(project_id=project_id, title=project_title or f"Imported project {project_id}", owner_ref=owner_ref)
        decision = self.get_decision(did)
        created = decision is None
        if decision is None:
            decision = self.create_decision(
                decision_id=did,
                project_id=project_id,
                decision_question=question,
                lifecycle_state=lifecycle_state,
                metadata={"imported_from_legacy_projection": True},
            )
        else:
            decision.decision_question = question
            decision.lifecycle_state = lifecycle_state
            if project_id:
                decision.project_id = project_id
        obj = self.upsert_unified_decision_object(
            did,
            payload=decision_object,
            schema_id=str(decision_object.get("schema") or "scds-decision-object/1.0"),
            provenance_ref=provenance_ref,
        )
        self._event(did, "decision_object.imported", {"source": "legacy-compatible", "idempotent": True})
        return decision, obj, created

    def authority_descriptor(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "authority": self.authority,
            "storage_authority": "python-postgresql",
            "live_write_authority": True,
            "final_decision_authority": "human-governed",
            "legacy_wordpress_packet_storage": "compatibility-preserved",
            "cutover_release": "3.4.0",
        }

    @staticmethod
    def project_dict(row: DecisionProject) -> dict[str, Any]:
        return _project_dict(row)

    @staticmethod
    def decision_dict(row: Decision) -> dict[str, Any]:
        return _decision_dict(row)

    @staticmethod
    def object_dict(row: DecisionObject) -> dict[str, Any]:
        return _object_dict(row)

    @staticmethod
    def snapshot_dict(row: Snapshot) -> dict[str, Any]:
        return _snapshot_dict(row)
