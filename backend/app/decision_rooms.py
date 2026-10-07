from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import secrets
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.persistence.models import (
    DecisionRoom,
    DecisionRoomChangeRequest,
    DecisionRoomComment,
    DecisionRoomEvent,
    DecisionRoomMember,
    DecisionRoomShareGrant,
    Snapshot,
)
from app.persistence.repository import PersistenceRepository

DECISION_ROOM_SCHEMA = "scds-collaborative-decision-room/2.0"
DECISION_ROOM_EVENT_SCHEMA = "scds-collaboration-event/2.0"
DECISION_ROOM_PERSISTENCE_SCHEMA = "scds-decision-room-python-persistence/1.0"
DECISION_ROOM_VERSION = "2.0"
ROOM_SNAPSHOT_TYPE = "decision-room"
ALLOWED_VISIBILITY = {"private", "restricted", "institutional"}
ALLOWED_ROLES = {"owner", "facilitator", "editor", "reviewer", "client", "observer"}
ROLE_PERMISSIONS = {
    "owner": ["manage_room", "manage_members", "comment", "request_change", "resolve", "snapshot", "lock", "share"],
    "facilitator": ["manage_members", "comment", "request_change", "resolve", "snapshot", "lock", "share"],
    "editor": ["comment", "request_change", "snapshot"],
    "reviewer": ["comment", "request_change", "resolve", "snapshot"],
    "client": ["comment", "request_change"],
    "observer": [],
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat().replace("+00:00", "Z") if value else None


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:24]}"


def _hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(raw).hexdigest()


def decision_room_contract() -> dict[str, Any]:
    return {
        "schema": DECISION_ROOM_SCHEMA,
        "event_schema": DECISION_ROOM_EVENT_SCHEMA,
        "persistence_schema": DECISION_ROOM_PERSISTENCE_SCHEMA,
        "version": DECISION_ROOM_VERSION,
        "role": "authoritative-python-postgresql-collaboration-and-decision-room-persistence",
        "storage_authority": "python-postgresql",
        "collaboration_authority": "decision-studio-kernel",
        "authentication_authority": "global-authentication-layer-planned-v3.14",
        "final_decision_authority": "human-governed",
        "tables": [
            "decision_rooms",
            "decision_room_members",
            "decision_room_comments",
            "decision_room_change_requests",
            "decision_room_share_grants",
            "decision_room_events",
            "snapshots",
        ],
        "principles": {
            "wordpress_is_not_canonical_room_persistence": True,
            "legacy_wordpress_room_projection_is_preserved": True,
            "room_membership_and_roles_are_persisted": True,
            "comments_are_human_records": True,
            "change_requests_are_human_records": True,
            "room_events_are_hash_chained": True,
            "share_tokens_are_stored_only_as_sha256_hashes": True,
            "room_snapshots_use_existing_snapshot_table": True,
            "ai_cannot_impersonate_participant": True,
            "ai_cannot_approve_or_sign": True,
            "room_activity_does_not_imply_decision_approval": True,
        },
        "security": {
            "read_scope": "rooms:read",
            "write_scope": "rooms:write",
            "repository_key_also_authorized": True,
        },
    }


def decision_room_template(decision_id: str = "") -> dict[str, Any]:
    return {
        "schema": DECISION_ROOM_SCHEMA,
        "event_schema": DECISION_ROOM_EVENT_SCHEMA,
        "persistence_schema": DECISION_ROOM_PERSISTENCE_SCHEMA,
        "room_id": "",
        "decision_id": decision_id,
        "title": "Collaborative Decision Room",
        "visibility": "private",
        "status": "active",
        "owner_ref": None,
        "members": [],
        "comments": [],
        "change_requests": [],
        "share_grants": [],
        "snapshots": [],
        "activity_timeline": [],
        "activity_integrity": {"ok": True, "event_count": 0, "problems": [], "head_hash": "GENESIS"},
        "canonical_persistence": "python-postgresql",
        "legacy_wordpress_projection": "compatibility-preserved",
        "final_decision_authority": "human-governed",
    }


class DecisionRoomUpsertRequest(BaseModel):
    room_id: str | None = Field(default=None, max_length=64)
    title: str = Field(default="Collaborative Decision Room", min_length=1, max_length=300)
    visibility: str = Field(default="private", max_length=64)
    status: str = Field(default="active", max_length=64)
    owner_ref: str | None = Field(default=None, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)
    actor_ref: str | None = Field(default=None, max_length=255)
    actor_role: str = Field(default="owner", max_length=64)


class DecisionRoomPatchRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    visibility: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default=None, max_length=64)
    owner_ref: str | None = Field(default=None, max_length=255)
    metadata: dict[str, Any] | None = None
    actor_ref: str | None = Field(default=None, max_length=255)
    actor_role: str = Field(default="owner", max_length=64)


class RoomMemberCreateRequest(BaseModel):
    member_id: str | None = Field(default=None, max_length=64)
    user_ref: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=320)
    name: str = Field(min_length=1, max_length=300)
    role: str = Field(default="observer", max_length=64)
    status: str = Field(default="active", max_length=64)
    invited_by: str | None = Field(default=None, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)
    actor_ref: str | None = Field(default=None, max_length=255)
    actor_role: str = Field(default="owner", max_length=64)


class RoomCommentCreateRequest(BaseModel):
    comment_id: str | None = Field(default=None, max_length=64)
    author_ref: str | None = Field(default=None, max_length=255)
    author_role: str = Field(default="reviewer", max_length=64)
    target_type: str = Field(default="decision", max_length=96)
    target_id: str | None = Field(default=None, max_length=255)
    content: str = Field(min_length=1, max_length=20000)
    visibility: str = Field(default="room", max_length=64)
    parent_comment_id: str | None = Field(default=None, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RoomCommentPatchRequest(BaseModel):
    status: str = Field(default="resolved", max_length=64)
    resolved_by: str | None = Field(default=None, max_length=255)
    resolution: str | None = Field(default=None, max_length=10000)
    actor_role: str = Field(default="reviewer", max_length=64)


class RoomChangeRequestCreate(BaseModel):
    change_request_id: str | None = Field(default=None, max_length=64)
    requested_by: str | None = Field(default=None, max_length=255)
    requester_role: str = Field(default="reviewer", max_length=64)
    target_type: str = Field(default="decision", max_length=96)
    target_id: str | None = Field(default=None, max_length=255)
    summary: str = Field(min_length=1, max_length=20000)
    packet_patch: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RoomChangeRequestPatch(BaseModel):
    status: str = Field(default="resolved", max_length=64)
    resolved_by: str | None = Field(default=None, max_length=255)
    resolution: str | None = Field(default=None, max_length=10000)
    actor_role: str = Field(default="reviewer", max_length=64)


class RoomSnapshotCreateRequest(BaseModel):
    snapshot_id: str | None = Field(default=None, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    provenance_ref: str | None = Field(default=None, max_length=255)
    label: str = Field(default="Decision Room snapshot", max_length=300)
    actor_ref: str | None = Field(default=None, max_length=255)
    actor_role: str = Field(default="reviewer", max_length=64)


class RoomShareGrantCreateRequest(BaseModel):
    member_id: str | None = Field(default=None, max_length=64)
    role: str = Field(default="observer", max_length=64)
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    actor_ref: str | None = Field(default=None, max_length=255)
    actor_role: str = Field(default="owner", max_length=64)


class DecisionRoomImportRequest(BaseModel):
    decision_id: str = Field(min_length=1, max_length=64)
    room: dict[str, Any] = Field(default_factory=dict)
    actor_ref: str | None = Field(default=None, max_length=255)


class DecisionRoomValidateRequest(BaseModel):
    room: dict[str, Any] = Field(default_factory=dict)
    strict: bool = True


def validate_decision_room(room: dict[str, Any], strict: bool = True) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if room.get("schema") != DECISION_ROOM_SCHEMA:
        errors.append("schema_mismatch")
    visibility = str(room.get("visibility") or "private")
    if visibility not in ALLOWED_VISIBILITY:
        errors.append("invalid_visibility")
    if room.get("canonical_persistence") not in {None, "python-postgresql"}:
        warnings.append("legacy_noncanonical_persistence_projection")
    seen: set[str] = set()
    for m in room.get("members") or []:
        mid = str(m.get("member_id") or "")
        if mid and mid in seen:
            errors.append(f"duplicate_member_id:{mid}")
        seen.add(mid)
        role = str(m.get("role") or "observer")
        if role not in ALLOWED_ROLES:
            errors.append(f"invalid_member_role:{role}")
    return {"ok": not errors, "strict": strict, "errors": errors, "warnings": warnings, "schema": DECISION_ROOM_SCHEMA}


class DecisionRoomRepository:
    def __init__(self, session: Session, *, app_version: str):
        self.session = session
        self.app_version = app_version
        self.repository = PersistenceRepository(session)

    def _decision(self, decision_id: str):
        row = self.repository.get_decision(decision_id)
        if row is None:
            raise LookupError("decision_not_found")
        return row

    def _room(self, room_id: str) -> DecisionRoom:
        row = self.session.get(DecisionRoom, room_id)
        if row is None:
            raise LookupError("decision_room_not_found")
        return row

    def _room_by_decision(self, decision_id: str) -> DecisionRoom | None:
        return self.session.scalar(select(DecisionRoom).where(DecisionRoom.decision_id == decision_id))

    def _event(self, room: DecisionRoom, event_type: str, *, actor_ref: str | None = None, actor_role: str | None = None, target_type: str = "room", target_id: str | None = None, payload: dict[str, Any] | None = None) -> DecisionRoomEvent:
        max_seq = self.session.scalar(select(func.max(DecisionRoomEvent.sequence_no)).where(DecisionRoomEvent.room_id == room.id)) or 0
        seq = int(max_seq) + 1
        previous_hash = room.head_event_hash or "GENESIS"
        event_body = {
            "event_schema": DECISION_ROOM_EVENT_SCHEMA,
            "room_id": room.id,
            "decision_id": room.decision_id,
            "sequence_no": seq,
            "event_type": event_type,
            "actor_ref": actor_ref,
            "actor_role": actor_role,
            "target_type": target_type,
            "target_id": target_id,
            "event_payload": payload or {},
            "previous_hash": previous_hash,
        }
        event_hash = _hash(event_body)
        row = DecisionRoomEvent(
            id=_id("room_evt"), room_id=room.id, decision_id=room.decision_id, sequence_no=seq,
            event_type=event_type, actor_ref=actor_ref, actor_role=actor_role, target_type=target_type,
            target_id=target_id, event_payload=payload or {}, previous_hash=previous_hash, event_hash=event_hash,
        )
        self.session.add(row)
        room.head_event_hash = event_hash
        self.repository._event(room.decision_id, f"decision_room.{event_type}", {"room_id": room.id, "room_event_hash": event_hash, **(payload or {})}, actor_ref=actor_ref)
        self.session.flush()
        return row

    def _room_dict(self, row: DecisionRoom, *, include_counts: bool = True) -> dict[str, Any]:
        out = {
            "schema": DECISION_ROOM_SCHEMA,
            "event_schema": DECISION_ROOM_EVENT_SCHEMA,
            "persistence_schema": DECISION_ROOM_PERSISTENCE_SCHEMA,
            "room_id": row.id,
            "decision_id": row.decision_id,
            "title": row.title,
            "visibility": row.visibility,
            "status": row.status,
            "owner_ref": row.owner_ref,
            "locked_snapshot_id": row.locked_snapshot_id,
            "head_event_hash": row.head_event_hash,
            "metadata": row.metadata_json or {},
            "created_at": _iso(row.created_at),
            "updated_at": _iso(row.updated_at),
            "canonical_persistence": "python-postgresql",
            "legacy_wordpress_projection": "compatibility-preserved",
            "final_decision_authority": "human-governed",
        }
        if include_counts:
            out["counts"] = {
                "members": self.session.scalar(select(func.count()).select_from(DecisionRoomMember).where(DecisionRoomMember.room_id == row.id)) or 0,
                "comments": self.session.scalar(select(func.count()).select_from(DecisionRoomComment).where(DecisionRoomComment.room_id == row.id)) or 0,
                "change_requests": self.session.scalar(select(func.count()).select_from(DecisionRoomChangeRequest).where(DecisionRoomChangeRequest.room_id == row.id)) or 0,
                "share_grants": self.session.scalar(select(func.count()).select_from(DecisionRoomShareGrant).where(DecisionRoomShareGrant.room_id == row.id)) or 0,
                "events": self.session.scalar(select(func.count()).select_from(DecisionRoomEvent).where(DecisionRoomEvent.room_id == row.id)) or 0,
                "snapshots": self.session.scalar(select(func.count()).select_from(Snapshot).where(Snapshot.decision_id == row.decision_id, Snapshot.snapshot_type == ROOM_SNAPSHOT_TYPE)) or 0,
            }
        return out

    @staticmethod
    def _member_dict(row: DecisionRoomMember) -> dict[str, Any]:
        return {"member_id": row.id, "room_id": row.room_id, "user_ref": row.user_ref, "email": row.email, "name": row.name, "role": row.role, "status": row.status, "invited_by": row.invited_by, "metadata": row.metadata_json or {}, "created_at": _iso(row.created_at), "updated_at": _iso(row.updated_at)}

    @staticmethod
    def _comment_dict(row: DecisionRoomComment) -> dict[str, Any]:
        return {"comment_id": row.id, "room_id": row.room_id, "author_ref": row.author_ref, "author_role": row.author_role, "target_type": row.target_type, "target_id": row.target_id, "content": row.content, "visibility": row.visibility, "status": row.status, "parent_comment_id": row.parent_comment_id, "resolved_by": row.resolved_by, "resolution": row.resolution, "metadata": row.metadata_json or {}, "created_at": _iso(row.created_at), "updated_at": _iso(row.updated_at)}

    @staticmethod
    def _change_dict(row: DecisionRoomChangeRequest) -> dict[str, Any]:
        return {"change_request_id": row.id, "room_id": row.room_id, "requested_by": row.requested_by, "requester_role": row.requester_role, "target_type": row.target_type, "target_id": row.target_id, "summary": row.summary, "status": row.status, "packet_patch": row.packet_patch or {}, "resolved_by": row.resolved_by, "resolution": row.resolution, "metadata": row.metadata_json or {}, "created_at": _iso(row.created_at), "updated_at": _iso(row.updated_at)}

    @staticmethod
    def _grant_dict(row: DecisionRoomShareGrant) -> dict[str, Any]:
        return {"grant_id": row.id, "room_id": row.room_id, "member_id": row.member_id, "role": row.role, "status": row.status, "expires_at": _iso(row.expires_at), "token_hint": row.token_hint, "created_by": row.created_by, "metadata": row.metadata_json or {}, "created_at": _iso(row.created_at), "updated_at": _iso(row.updated_at)}

    @staticmethod
    def _event_dict(row: DecisionRoomEvent) -> dict[str, Any]:
        return {"event_schema": DECISION_ROOM_EVENT_SCHEMA, "event_id": row.id, "room_id": row.room_id, "decision_id": row.decision_id, "sequence": row.sequence_no, "event_type": row.event_type, "actor_ref": row.actor_ref, "actor_role": row.actor_role, "target_type": row.target_type, "target_id": row.target_id, "details": row.event_payload or {}, "previous_hash": row.previous_hash, "event_hash": row.event_hash, "recorded_at": _iso(row.occurred_at)}

    def upsert_for_decision(self, decision_id: str, req: DecisionRoomUpsertRequest) -> dict[str, Any]:
        self._decision(decision_id)
        visibility = req.visibility.lower().strip()
        if visibility not in ALLOWED_VISIBILITY:
            raise ValueError("invalid_visibility")
        role = req.actor_role.lower().strip()
        if role not in ALLOWED_ROLES:
            raise ValueError("invalid_actor_role")
        row = self._room_by_decision(decision_id)
        created = row is None
        if row is None:
            row = DecisionRoom(
                id=req.room_id or _id("room"), decision_id=decision_id, title=req.title,
                visibility=visibility, status=req.status, owner_ref=req.owner_ref or req.actor_ref,
                room_schema=DECISION_ROOM_SCHEMA, metadata_json=req.metadata or {}, head_event_hash="GENESIS",
            )
            self.session.add(row); self.session.flush()
            if req.actor_ref:
                member = DecisionRoomMember(id=_id("member"), room_id=row.id, user_ref=req.actor_ref, email=None, name=req.actor_ref, role="owner", status="active", invited_by=req.actor_ref, metadata_json={"created_with_room": True})
                self.session.add(member); self.session.flush()
            self._event(row, "created", actor_ref=req.actor_ref, actor_role=role, payload={"visibility": visibility, "owner_ref": row.owner_ref})
        else:
            row.title=req.title; row.visibility=visibility; row.status=req.status; row.owner_ref=req.owner_ref or row.owner_ref; row.metadata_json=req.metadata or {}
            self.session.flush(); self._event(row, "updated", actor_ref=req.actor_ref, actor_role=role, payload={"fields": ["title","visibility","status","owner_ref","metadata"]})
        out=self._room_dict(row); out["created"] = created; return out

    def get_by_decision(self, decision_id: str) -> dict[str, Any]:
        self._decision(decision_id)
        row=self._room_by_decision(decision_id)
        if row is None: raise LookupError("decision_room_not_found")
        return self._room_dict(row)

    def get(self, room_id: str) -> dict[str, Any]:
        return self._room_dict(self._room(room_id))

    def patch(self, room_id: str, req: DecisionRoomPatchRequest) -> dict[str, Any]:
        row=self._room(room_id)
        if req.visibility is not None:
            v=req.visibility.lower().strip()
            if v not in ALLOWED_VISIBILITY: raise ValueError("invalid_visibility")
            row.visibility=v
        if req.title is not None: row.title=req.title
        if req.status is not None: row.status=req.status
        if req.owner_ref is not None: row.owner_ref=req.owner_ref
        if req.metadata is not None: row.metadata_json=req.metadata
        self.session.flush(); self._event(row,"updated",actor_ref=req.actor_ref,actor_role=req.actor_role,payload={"status":row.status,"visibility":row.visibility})
        return self._room_dict(row)

    def add_member(self, room_id: str, req: RoomMemberCreateRequest) -> dict[str, Any]:
        room=self._room(room_id); role=req.role.lower().strip(); actor_role=req.actor_role.lower().strip()
        if role not in ALLOWED_ROLES: raise ValueError("invalid_member_role")
        if "manage_members" not in ROLE_PERMISSIONS.get(actor_role,[]): raise PermissionError("manage_members_permission_required")
        row=DecisionRoomMember(id=req.member_id or _id("member"),room_id=room_id,user_ref=req.user_ref,email=(req.email or None),name=req.name,role=role,status=req.status,invited_by=req.invited_by or req.actor_ref,metadata_json=req.metadata or {})
        self.session.add(row); self.session.flush(); self._event(room,"member_added",actor_ref=req.actor_ref,actor_role=req.actor_role,target_type="member",target_id=row.id,payload={"role":role})
        return self._member_dict(row)

    def members(self, room_id: str) -> list[dict[str, Any]]:
        self._room(room_id); rows=self.session.scalars(select(DecisionRoomMember).where(DecisionRoomMember.room_id==room_id).order_by(DecisionRoomMember.created_at)).all(); return [self._member_dict(x) for x in rows]

    def add_comment(self, room_id: str, req: RoomCommentCreateRequest) -> dict[str, Any]:
        room=self._room(room_id); role=req.author_role.lower().strip()
        if role not in ALLOWED_ROLES: raise ValueError("invalid_author_role")
        if "comment" not in ROLE_PERMISSIONS.get(role,[]): raise PermissionError("comment_permission_required")
        row=DecisionRoomComment(id=req.comment_id or _id("comment"),room_id=room_id,author_ref=req.author_ref,author_role=role,target_type=req.target_type,target_id=req.target_id,content=req.content,visibility=req.visibility,status="open",parent_comment_id=req.parent_comment_id,metadata_json=req.metadata or {})
        self.session.add(row); self.session.flush(); self._event(room,"comment_added",actor_ref=req.author_ref,actor_role=role,target_type="comment",target_id=row.id,payload={"target_type":req.target_type,"target_id":req.target_id})
        return self._comment_dict(row)

    def comments(self, room_id: str) -> list[dict[str, Any]]:
        self._room(room_id); rows=self.session.scalars(select(DecisionRoomComment).where(DecisionRoomComment.room_id==room_id).order_by(DecisionRoomComment.created_at)).all(); return [self._comment_dict(x) for x in rows]

    def patch_comment(self, room_id: str, comment_id: str, req: RoomCommentPatchRequest) -> dict[str, Any]:
        room=self._room(room_id); row=self.session.get(DecisionRoomComment,comment_id)
        if row is None or row.room_id!=room_id: raise LookupError("decision_room_comment_not_found")
        role=req.actor_role.lower().strip()
        if "resolve" not in ROLE_PERMISSIONS.get(role,[]): raise PermissionError("resolve_permission_required")
        row.status=req.status; row.resolved_by=req.resolved_by; row.resolution=req.resolution; self.session.flush(); self._event(room,"comment_updated",actor_ref=req.resolved_by,actor_role=role,target_type="comment",target_id=row.id,payload={"status":row.status})
        return self._comment_dict(row)

    def add_change_request(self, room_id: str, req: RoomChangeRequestCreate) -> dict[str, Any]:
        room=self._room(room_id); role=req.requester_role.lower().strip()
        if "request_change" not in ROLE_PERMISSIONS.get(role,[]): raise PermissionError("request_change_permission_required")
        row=DecisionRoomChangeRequest(id=req.change_request_id or _id("change"),room_id=room_id,requested_by=req.requested_by,requester_role=role,target_type=req.target_type,target_id=req.target_id,summary=req.summary,status="open",packet_patch=req.packet_patch or {},metadata_json=req.metadata or {})
        self.session.add(row); self.session.flush(); self._event(room,"change_request_added",actor_ref=req.requested_by,actor_role=role,target_type="change_request",target_id=row.id,payload={"target_type":req.target_type,"target_id":req.target_id})
        return self._change_dict(row)

    def change_requests(self, room_id: str) -> list[dict[str, Any]]:
        self._room(room_id); rows=self.session.scalars(select(DecisionRoomChangeRequest).where(DecisionRoomChangeRequest.room_id==room_id).order_by(DecisionRoomChangeRequest.created_at)).all(); return [self._change_dict(x) for x in rows]

    def patch_change_request(self, room_id: str, change_id: str, req: RoomChangeRequestPatch) -> dict[str, Any]:
        room=self._room(room_id); row=self.session.get(DecisionRoomChangeRequest,change_id)
        if row is None or row.room_id!=room_id: raise LookupError("decision_room_change_request_not_found")
        role=req.actor_role.lower().strip()
        if "resolve" not in ROLE_PERMISSIONS.get(role,[]): raise PermissionError("resolve_permission_required")
        row.status=req.status; row.resolved_by=req.resolved_by; row.resolution=req.resolution; self.session.flush(); self._event(room,"change_request_updated",actor_ref=req.resolved_by,actor_role=role,target_type="change_request",target_id=row.id,payload={"status":row.status})
        return self._change_dict(row)

    def create_snapshot(self, room_id: str, req: RoomSnapshotCreateRequest) -> dict[str, Any]:
        room=self._room(room_id); role=req.actor_role.lower().strip()
        if "snapshot" not in ROLE_PERMISSIONS.get(role,[]): raise PermissionError("snapshot_permission_required")
        payload={"schema":DECISION_ROOM_SCHEMA,"room_id":room.id,"decision_id":room.decision_id,"label":req.label,"room":self._room_dict(room),"payload":req.payload}
        row=Snapshot(id=req.snapshot_id or _id("room_snap"),decision_id=room.decision_id,snapshot_type=ROOM_SNAPSHOT_TYPE,payload=payload,provenance_ref=req.provenance_ref or req.actor_ref)
        self.session.add(row); self.session.flush(); self._event(room,"snapshot_created",actor_ref=req.actor_ref,actor_role=role,target_type="snapshot",target_id=row.id,payload={"content_sha256":_hash(payload),"label":req.label})
        return {"snapshot_id":row.id,"room_id":room.id,"decision_id":room.decision_id,"snapshot_type":row.snapshot_type,"payload":row.payload,"provenance_ref":row.provenance_ref,"created_at":_iso(row.created_at),"content_sha256":_hash(row.payload)}

    def snapshots(self, room_id: str) -> list[dict[str, Any]]:
        room=self._room(room_id); rows=self.session.scalars(select(Snapshot).where(Snapshot.decision_id==room.decision_id,Snapshot.snapshot_type==ROOM_SNAPSHOT_TYPE).order_by(Snapshot.created_at)).all(); return [{"snapshot_id":x.id,"room_id":room.id,"decision_id":x.decision_id,"snapshot_type":x.snapshot_type,"payload":x.payload,"provenance_ref":x.provenance_ref,"created_at":_iso(x.created_at),"content_sha256":_hash(x.payload)} for x in rows]

    def create_share_grant(self, room_id: str, req: RoomShareGrantCreateRequest) -> tuple[dict[str, Any], str]:
        room=self._room(room_id); role=req.actor_role.lower().strip(); granted_role=req.role.lower().strip()
        if "share" not in ROLE_PERMISSIONS.get(role,[]): raise PermissionError("share_permission_required")
        if granted_role not in ALLOWED_ROLES: raise ValueError("invalid_share_role")
        member=None
        if req.member_id:
            member=self.session.get(DecisionRoomMember,req.member_id)
            if member is None or member.room_id!=room_id: raise LookupError("decision_room_member_not_found")
        token=secrets.token_urlsafe(32); digest=sha256(token.encode()).hexdigest()
        row=DecisionRoomShareGrant(id=_id("grant"),room_id=room_id,member_id=req.member_id,role=granted_role,status="active",expires_at=req.expires_at,token_hash=digest,token_hint=f"{token[:4]}…{token[-4:]}",created_by=req.actor_ref,metadata_json=req.metadata or {})
        self.session.add(row); self.session.flush(); self._event(room,"share_grant_created",actor_ref=req.actor_ref,actor_role=role,target_type="share_grant",target_id=row.id,payload={"member_id":req.member_id,"role":granted_role,"expires_at":_iso(req.expires_at)})
        return self._grant_dict(row), token

    def share_grants(self, room_id: str) -> list[dict[str, Any]]:
        self._room(room_id); rows=self.session.scalars(select(DecisionRoomShareGrant).where(DecisionRoomShareGrant.room_id==room_id).order_by(DecisionRoomShareGrant.created_at)).all(); return [self._grant_dict(x) for x in rows]

    def events(self, room_id: str) -> dict[str, Any]:
        room=self._room(room_id); rows=self.session.scalars(select(DecisionRoomEvent).where(DecisionRoomEvent.room_id==room_id).order_by(DecisionRoomEvent.sequence_no)).all(); events=[self._event_dict(x) for x in rows]
        previous="GENESIS"; problems=[]
        for e in events:
            if e["previous_hash"] != previous: problems.append({"sequence":e["sequence"],"code":"previous_hash_mismatch"})
            body={"event_schema":DECISION_ROOM_EVENT_SCHEMA,"room_id":e["room_id"],"decision_id":e["decision_id"],"sequence_no":e["sequence"],"event_type":e["event_type"],"actor_ref":e["actor_ref"],"actor_role":e["actor_role"],"target_type":e["target_type"],"target_id":e["target_id"],"event_payload":e["details"],"previous_hash":e["previous_hash"]}
            if _hash(body) != e["event_hash"]: problems.append({"sequence":e["sequence"],"code":"event_hash_mismatch"})
            previous=e["event_hash"]
        if previous != room.head_event_hash: problems.append({"code":"head_hash_mismatch"})
        return {"room_id":room_id,"events":events,"integrity":{"ok":not problems,"event_count":len(events),"problems":problems,"head_hash":room.head_event_hash}}

    def import_legacy(self, req: DecisionRoomImportRequest) -> dict[str, Any]:
        legacy=req.room or {}
        room=self.upsert_for_decision(req.decision_id, DecisionRoomUpsertRequest(
            room_id=str(legacy.get("room_id") or "") or None,
            title=str(legacy.get("title") or "Collaborative Decision Room"), visibility=str(legacy.get("visibility") or "private"), status=str(legacy.get("status") or "active"),
            owner_ref=str((legacy.get("owner") or {}).get("name") or req.actor_ref or "") or None,
            metadata={"legacy_wordpress_source_preserved":True,"legacy_room_schema":legacy.get("schema"),"source_representation_sha256":_hash(legacy)}, actor_ref=None, actor_role="owner"))
        room_id=room["room_id"]
        # Import child records only when canonical table is still empty; makes import idempotent.
        if not self.members(room_id):
            for m in legacy.get("members") or []:
                role=str(m.get("role") or "observer"); role=role if role in ALLOWED_ROLES else "observer"
                self.add_member(room_id, RoomMemberCreateRequest(member_id=str(m.get("member_id") or "") or None,user_ref=str(m.get("user_id") or "") or None,email=str(m.get("email") or "") or None,name=str(m.get("name") or m.get("email") or "Imported participant"),role=role,status=str(m.get("status") or "active"),invited_by=str(m.get("invited_by") or req.actor_ref or "") or None,metadata={"legacy_import":True},actor_ref=req.actor_ref,actor_role="owner"))
        if not self.comments(room_id):
            for c in legacy.get("comments") or []:
                role=str(c.get("author_role") or "reviewer"); role=role if role in ALLOWED_ROLES else "reviewer"
                self.add_comment(room_id, RoomCommentCreateRequest(comment_id=str(c.get("comment_id") or "") or None,author_ref=str(c.get("author") or "") or None,author_role=role,target_type=str(c.get("target_type") or "decision"),target_id=str(c.get("target_id") or "") or None,content=str(c.get("content") or "Imported legacy comment"),visibility=str(c.get("visibility") or "room"),parent_comment_id=str(c.get("parent_comment_id") or "") or None,metadata={"legacy_import":True}))
        self._event(self._room(room_id),"legacy_wordpress_room_imported",actor_ref=req.actor_ref,actor_role="owner",payload={"source_representation_sha256":_hash(legacy),"legacy_source_preserved":True})
        return {"room":self.get(room_id),"legacy_source_preserved":True,"idempotent":True}
