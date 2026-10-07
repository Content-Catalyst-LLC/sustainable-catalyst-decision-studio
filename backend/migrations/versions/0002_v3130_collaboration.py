"""Decision Studio v3.13.0 collaboration and decision room Python persistence.

Revision ID: 0002_v3130_collaboration
Revises: 0001_v330_pg_foundation
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0002_v3130_collaboration"
down_revision = "0001_v330_pg_foundation"
branch_labels = None
depends_on = None


def _timestamps():
    return [sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False)]

def upgrade() -> None:
    op.create_table("decision_rooms",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("decision_id", sa.String(64), sa.ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("visibility", sa.String(64), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("owner_ref", sa.String(255)),
        sa.Column("room_schema", sa.String(255), nullable=False),
        sa.Column("locked_snapshot_id", sa.String(64)),
        sa.Column("head_event_hash", sa.String(64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False), *_timestamps(),
        sa.UniqueConstraint("decision_id", name="uq_decision_room_decision"))
    op.create_index("ix_decision_rooms_decision_id", "decision_rooms", ["decision_id"] )
    op.create_table("decision_room_members",
        sa.Column("id", sa.String(64), primary_key=True), sa.Column("room_id", sa.String(64), sa.ForeignKey("decision_rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_ref", sa.String(255)), sa.Column("email", sa.String(320)), sa.Column("name", sa.String(300), nullable=False), sa.Column("role", sa.String(64), nullable=False), sa.Column("status", sa.String(64), nullable=False), sa.Column("invited_by", sa.String(255)), sa.Column("metadata_json", sa.JSON(), nullable=False), *_timestamps())
    op.create_index("ix_decision_room_members_room_id", "decision_room_members", ["room_id"]); op.create_index("ix_decision_room_members_user_ref", "decision_room_members", ["user_ref"]); op.create_index("ix_decision_room_members_email", "decision_room_members", ["email"])
    op.create_table("decision_room_comments",
        sa.Column("id", sa.String(64), primary_key=True), sa.Column("room_id", sa.String(64), sa.ForeignKey("decision_rooms.id", ondelete="CASCADE"), nullable=False), sa.Column("author_ref", sa.String(255)), sa.Column("author_role", sa.String(64), nullable=False), sa.Column("target_type", sa.String(96), nullable=False), sa.Column("target_id", sa.String(255)), sa.Column("content", sa.Text(), nullable=False), sa.Column("visibility", sa.String(64), nullable=False), sa.Column("status", sa.String(64), nullable=False), sa.Column("parent_comment_id", sa.String(64)), sa.Column("resolved_by", sa.String(255)), sa.Column("resolution", sa.Text()), sa.Column("metadata_json", sa.JSON(), nullable=False), *_timestamps())
    op.create_index("ix_decision_room_comments_room_id", "decision_room_comments", ["room_id"]); op.create_index("ix_decision_room_comments_author_ref", "decision_room_comments", ["author_ref"])
    op.create_table("decision_room_change_requests",
        sa.Column("id", sa.String(64), primary_key=True), sa.Column("room_id", sa.String(64), sa.ForeignKey("decision_rooms.id", ondelete="CASCADE"), nullable=False), sa.Column("requested_by", sa.String(255)), sa.Column("requester_role", sa.String(64), nullable=False), sa.Column("target_type", sa.String(96), nullable=False), sa.Column("target_id", sa.String(255)), sa.Column("summary", sa.Text(), nullable=False), sa.Column("status", sa.String(64), nullable=False), sa.Column("packet_patch", sa.JSON(), nullable=False), sa.Column("resolved_by", sa.String(255)), sa.Column("resolution", sa.Text()), sa.Column("metadata_json", sa.JSON(), nullable=False), *_timestamps())
    op.create_index("ix_decision_room_change_requests_room_id", "decision_room_change_requests", ["room_id"]); op.create_index("ix_decision_room_change_requests_requested_by", "decision_room_change_requests", ["requested_by"])
    op.create_table("decision_room_share_grants",
        sa.Column("id", sa.String(64), primary_key=True), sa.Column("room_id", sa.String(64), sa.ForeignKey("decision_rooms.id", ondelete="CASCADE"), nullable=False), sa.Column("member_id", sa.String(64), sa.ForeignKey("decision_room_members.id", ondelete="SET NULL")), sa.Column("role", sa.String(64), nullable=False), sa.Column("status", sa.String(64), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True)), sa.Column("token_hash", sa.String(64), nullable=False, unique=True), sa.Column("token_hint", sa.String(32)), sa.Column("created_by", sa.String(255)), sa.Column("metadata_json", sa.JSON(), nullable=False), *_timestamps())
    op.create_index("ix_decision_room_share_grants_room_id", "decision_room_share_grants", ["room_id"]); op.create_index("ix_decision_room_share_grants_member_id", "decision_room_share_grants", ["member_id"])
    op.create_table("decision_room_events",
        sa.Column("id", sa.String(64), primary_key=True), sa.Column("room_id", sa.String(64), sa.ForeignKey("decision_rooms.id", ondelete="CASCADE"), nullable=False), sa.Column("decision_id", sa.String(64), sa.ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False), sa.Column("sequence_no", sa.Integer(), nullable=False), sa.Column("event_type", sa.String(128), nullable=False), sa.Column("actor_ref", sa.String(255)), sa.Column("actor_role", sa.String(64)), sa.Column("target_type", sa.String(96), nullable=False), sa.Column("target_id", sa.String(255)), sa.Column("event_payload", sa.JSON(), nullable=False), sa.Column("previous_hash", sa.String(64), nullable=False), sa.Column("event_hash", sa.String(64), nullable=False, unique=True), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("room_id", "sequence_no", name="uq_decision_room_event_sequence"))
    op.create_index("ix_decision_room_events_room_id", "decision_room_events", ["room_id"]); op.create_index("ix_decision_room_events_decision_id", "decision_room_events", ["decision_id"]); op.create_index("ix_decision_room_events_event_type", "decision_room_events", ["event_type"]); op.create_index("ix_decision_room_events_occurred_at", "decision_room_events", ["occurred_at"])

def downgrade() -> None:
    for name in ["decision_room_events","decision_room_share_grants","decision_room_change_requests","decision_room_comments","decision_room_members","decision_rooms"]:
        op.drop_table(name)
