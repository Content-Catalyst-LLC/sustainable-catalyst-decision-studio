from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class DecisionProject(Base, TimestampMixin):
    __tablename__ = "decision_projects"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="active")
    owner_ref: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class Decision(Base, TimestampMixin):
    __tablename__ = "decisions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("decision_projects.id", ondelete="SET NULL"), index=True)
    decision_question: Mapped[str] = mapped_column(Text, nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(64), nullable=False, default="framing")
    final_decision_authority: Mapped[str] = mapped_column(String(64), nullable=False, default="human-governed")
    current_snapshot_id: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class DecisionObject(Base, TimestampMixin):
    __tablename__ = "decision_objects"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), index=True)
    object_type: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    schema_id: Mapped[str | None] = mapped_column(String(255))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    provenance_ref: Mapped[str | None] = mapped_column(String(255))


class DecisionModule(Base, TimestampMixin):
    __tablename__ = "decision_modules"
    module_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="foundation")
    contract_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class DecisionModuleBinding(Base, TimestampMixin):
    __tablename__ = "decision_module_bindings"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), index=True)
    module_id: Mapped[str] = mapped_column(ForeignKey("decision_modules.module_id", ondelete="RESTRICT"), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    __table_args__ = (UniqueConstraint("decision_id", "module_id", name="uq_decision_module_binding"),)


class Alternative(Base, TimestampMixin):
    __tablename__ = "alternatives"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="candidate")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class Criterion(Base, TimestampMixin):
    __tablename__ = "criteria"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    weight: Mapped[str | None] = mapped_column(String(64))
    direction: Mapped[str | None] = mapped_column(String(32))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CriterionValue(Base, TimestampMixin):
    __tablename__ = "criterion_values"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    criterion_id: Mapped[str] = mapped_column(ForeignKey("criteria.id", ondelete="CASCADE"), index=True)
    alternative_id: Mapped[str] = mapped_column(ForeignKey("alternatives.id", ondelete="CASCADE"), index=True)
    value_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    evidence_ref: Mapped[str | None] = mapped_column(String(255))
    __table_args__ = (UniqueConstraint("criterion_id", "alternative_id", name="uq_criterion_alternative_value"),)


class Assumption(Base, TimestampMixin):
    __tablename__ = "assumptions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="open")
    confidence: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class Claim(Base, TimestampMixin):
    __tablename__ = "claims"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    epistemic_status: Mapped[str] = mapped_column(String(64), nullable=False, default="unresolved")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class EvidenceLink(Base, TimestampMixin):
    __tablename__ = "evidence_links"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), index=True)
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.id", ondelete="SET NULL"), index=True)
    evidence_ref: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    relation: Mapped[str] = mapped_column(String(64), nullable=False, default="supports")
    provenance_ref: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class Scenario(Base, TimestampMixin):
    __tablename__ = "scenarios"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="draft")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ScenarioVariable(Base, TimestampMixin):
    __tablename__ = "scenario_variables"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source_ref: Mapped[str | None] = mapped_column(String(255))


class UncertaintyModel(Base, TimestampMixin):
    __tablename__ = "uncertainty_models"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), index=True)
    model_type: Mapped[str] = mapped_column(String(96), nullable=False)
    specification: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    computation_ref: Mapped[str | None] = mapped_column(String(255))
    provenance_ref: Mapped[str | None] = mapped_column(String(255))


class Recommendation(Base, TimestampMixin):
    __tablename__ = "recommendations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="candidate")
    recommendation_text: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    human_disposition: Mapped[str | None] = mapped_column(String(64))


class Review(Base, TimestampMixin):
    __tablename__ = "reviews"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), index=True)
    recommendation_id: Mapped[str | None] = mapped_column(ForeignKey("recommendations.id", ondelete="SET NULL"), index=True)
    reviewer_ref: Mapped[str | None] = mapped_column(String(255))
    disposition: Mapped[str | None] = mapped_column(String(64))
    review_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class Challenge(Base, TimestampMixin):
    __tablename__ = "challenges"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), index=True)
    recommendation_id: Mapped[str | None] = mapped_column(ForeignKey("recommendations.id", ondelete="SET NULL"), index=True)
    challenge_type: Mapped[str] = mapped_column(String(96), nullable=False, default="general")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="open")
    challenge_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class DecisionEvent(Base):
    __tablename__ = "decision_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    actor_ref: Mapped[str | None] = mapped_column(String(255))
    event_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    sequence_no: Mapped[int | None] = mapped_column(Integer)
    __table_args__ = (Index("ix_decision_events_decision_sequence", "decision_id", "sequence_no"),)


class Artifact(Base, TimestampMixin):
    __tablename__ = "artifacts"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision_id: Mapped[str | None] = mapped_column(ForeignKey("decisions.id", ondelete="SET NULL"), index=True)
    artifact_type: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    schema_id: Mapped[str | None] = mapped_column(String(255))
    uri: Mapped[str | None] = mapped_column(Text)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    provenance_ref: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class DecisionRoom(Base, TimestampMixin):
    __tablename__ = "decision_rooms"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    visibility: Mapped[str] = mapped_column(String(64), nullable=False, default="private")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="active")
    owner_ref: Mapped[str | None] = mapped_column(String(255))
    room_schema: Mapped[str] = mapped_column(String(255), nullable=False, default="scds-collaborative-decision-room/2.0")
    locked_snapshot_id: Mapped[str | None] = mapped_column(String(64))
    head_event_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="GENESIS")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    __table_args__ = (UniqueConstraint("decision_id", name="uq_decision_room_decision"),)


class DecisionRoomMember(Base, TimestampMixin):
    __tablename__ = "decision_room_members"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    room_id: Mapped[str] = mapped_column(ForeignKey("decision_rooms.id", ondelete="CASCADE"), index=True, nullable=False)
    user_ref: Mapped[str | None] = mapped_column(String(255), index=True)
    email: Mapped[str | None] = mapped_column(String(320), index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="observer")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="active")
    invited_by: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class DecisionRoomComment(Base, TimestampMixin):
    __tablename__ = "decision_room_comments"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    room_id: Mapped[str] = mapped_column(ForeignKey("decision_rooms.id", ondelete="CASCADE"), index=True, nullable=False)
    author_ref: Mapped[str | None] = mapped_column(String(255), index=True)
    author_role: Mapped[str] = mapped_column(String(64), nullable=False, default="observer")
    target_type: Mapped[str] = mapped_column(String(96), nullable=False, default="decision")
    target_id: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(64), nullable=False, default="room")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="open")
    parent_comment_id: Mapped[str | None] = mapped_column(String(64))
    resolved_by: Mapped[str | None] = mapped_column(String(255))
    resolution: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class DecisionRoomChangeRequest(Base, TimestampMixin):
    __tablename__ = "decision_room_change_requests"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    room_id: Mapped[str] = mapped_column(ForeignKey("decision_rooms.id", ondelete="CASCADE"), index=True, nullable=False)
    requested_by: Mapped[str | None] = mapped_column(String(255), index=True)
    requester_role: Mapped[str] = mapped_column(String(64), nullable=False, default="reviewer")
    target_type: Mapped[str] = mapped_column(String(96), nullable=False, default="decision")
    target_id: Mapped[str | None] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="open")
    packet_patch: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    resolved_by: Mapped[str | None] = mapped_column(String(255))
    resolution: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class DecisionRoomShareGrant(Base, TimestampMixin):
    __tablename__ = "decision_room_share_grants"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    room_id: Mapped[str] = mapped_column(ForeignKey("decision_rooms.id", ondelete="CASCADE"), index=True, nullable=False)
    member_id: Mapped[str | None] = mapped_column(ForeignKey("decision_room_members.id", ondelete="SET NULL"), index=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="observer")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="active")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    token_hint: Mapped[str | None] = mapped_column(String(32))
    created_by: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class DecisionRoomEvent(Base):
    __tablename__ = "decision_room_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    room_id: Mapped[str] = mapped_column(ForeignKey("decision_rooms.id", ondelete="CASCADE"), index=True, nullable=False)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), index=True, nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    actor_ref: Mapped[str | None] = mapped_column(String(255))
    actor_role: Mapped[str | None] = mapped_column(String(64))
    target_type: Mapped[str] = mapped_column(String(96), nullable=False, default="room")
    target_id: Mapped[str | None] = mapped_column(String(255))
    event_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    __table_args__ = (UniqueConstraint("room_id", "sequence_no", name="uq_decision_room_event_sequence"),)


class Snapshot(Base):
    __tablename__ = "snapshots"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), index=True)
    snapshot_type: Mapped[str] = mapped_column(String(96), nullable=False, default="decision")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    provenance_ref: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
