"""Decision Studio v3.3.1 PostgreSQL migration revision repair.

Revision ID: 0001_v330_pg_foundation
Revises: None
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_v330_pg_foundation"
down_revision = None
branch_labels = None
depends_on = None


def _metadata() -> sa.MetaData:
    m = sa.MetaData()
    timestamps = lambda: [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]
    sa.Table("decision_projects", m,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("owner_ref", sa.String(255)),
        sa.Column("metadata_json", sa.JSON(), nullable=False), *timestamps())
    sa.Table("decisions", m,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("project_id", sa.String(64), sa.ForeignKey("decision_projects.id", ondelete="SET NULL"), index=True),
        sa.Column("decision_question", sa.Text(), nullable=False),
        sa.Column("lifecycle_state", sa.String(64), nullable=False),
        sa.Column("final_decision_authority", sa.String(64), nullable=False),
        sa.Column("current_snapshot_id", sa.String(64)),
        sa.Column("metadata_json", sa.JSON(), nullable=False), *timestamps())
    sa.Table("decision_objects", m,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("decision_id", sa.String(64), sa.ForeignKey("decisions.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("object_type", sa.String(96), nullable=False, index=True),
        sa.Column("schema_id", sa.String(255)),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("provenance_ref", sa.String(255)), *timestamps())
    sa.Table("decision_modules", m,
        sa.Column("module_id", sa.String(64), primary_key=True),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("contract_version", sa.String(64), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("contract_json", sa.JSON(), nullable=False), *timestamps())
    sa.Table("decision_module_bindings", m,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("decision_id", sa.String(64), sa.ForeignKey("decisions.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("module_id", sa.String(64), sa.ForeignKey("decision_modules.module_id", ondelete="RESTRICT"), index=True, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False), *timestamps(),
        sa.UniqueConstraint("decision_id", "module_id", name="uq_decision_module_binding"))
    sa.Table("alternatives", m,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("decision_id", sa.String(64), sa.ForeignKey("decisions.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False), *timestamps())
    sa.Table("criteria", m,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("decision_id", sa.String(64), sa.ForeignKey("decisions.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("weight", sa.String(64)),
        sa.Column("direction", sa.String(32)),
        sa.Column("metadata_json", sa.JSON(), nullable=False), *timestamps())
    sa.Table("criterion_values", m,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("criterion_id", sa.String(64), sa.ForeignKey("criteria.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("alternative_id", sa.String(64), sa.ForeignKey("alternatives.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("evidence_ref", sa.String(255)), *timestamps(),
        sa.UniqueConstraint("criterion_id", "alternative_id", name="uq_criterion_alternative_value"))
    sa.Table("assumptions", m,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("decision_id", sa.String(64), sa.ForeignKey("decisions.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("confidence", sa.String(64)),
        sa.Column("metadata_json", sa.JSON(), nullable=False), *timestamps())
    sa.Table("claims", m,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("decision_id", sa.String(64), sa.ForeignKey("decisions.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("epistemic_status", sa.String(64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False), *timestamps())
    sa.Table("evidence_links", m,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("decision_id", sa.String(64), sa.ForeignKey("decisions.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("claim_id", sa.String(64), sa.ForeignKey("claims.id", ondelete="SET NULL"), index=True),
        sa.Column("evidence_ref", sa.String(255), nullable=False, index=True),
        sa.Column("relation", sa.String(64), nullable=False),
        sa.Column("provenance_ref", sa.String(255)),
        sa.Column("metadata_json", sa.JSON(), nullable=False), *timestamps())
    sa.Table("scenarios", m,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("decision_id", sa.String(64), sa.ForeignKey("decisions.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False), *timestamps())
    sa.Table("scenario_variables", m,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("scenario_id", sa.String(64), sa.ForeignKey("scenarios.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("source_ref", sa.String(255)), *timestamps())
    sa.Table("uncertainty_models", m,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("decision_id", sa.String(64), sa.ForeignKey("decisions.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("model_type", sa.String(96), nullable=False),
        sa.Column("specification", sa.JSON(), nullable=False),
        sa.Column("computation_ref", sa.String(255)),
        sa.Column("provenance_ref", sa.String(255)), *timestamps())
    sa.Table("recommendations", m,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("decision_id", sa.String(64), sa.ForeignKey("decisions.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("recommendation_text", sa.Text(), nullable=False),
        sa.Column("rationale", sa.JSON(), nullable=False),
        sa.Column("human_disposition", sa.String(64)), *timestamps())
    sa.Table("reviews", m,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("decision_id", sa.String(64), sa.ForeignKey("decisions.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("recommendation_id", sa.String(64), sa.ForeignKey("recommendations.id", ondelete="SET NULL"), index=True),
        sa.Column("reviewer_ref", sa.String(255)),
        sa.Column("disposition", sa.String(64)),
        sa.Column("review_json", sa.JSON(), nullable=False), *timestamps())
    sa.Table("challenges", m,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("decision_id", sa.String(64), sa.ForeignKey("decisions.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("recommendation_id", sa.String(64), sa.ForeignKey("recommendations.id", ondelete="SET NULL"), index=True),
        sa.Column("challenge_type", sa.String(96), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("challenge_json", sa.JSON(), nullable=False), *timestamps())
    sa.Table("decision_events", m,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("decision_id", sa.String(64), sa.ForeignKey("decisions.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False, index=True),
        sa.Column("actor_ref", sa.String(255)),
        sa.Column("event_payload", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("sequence_no", sa.Integer()),
        sa.Index("ix_decision_events_decision_sequence", "decision_id", "sequence_no"))
    sa.Table("artifacts", m,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("decision_id", sa.String(64), sa.ForeignKey("decisions.id", ondelete="SET NULL"), index=True),
        sa.Column("artifact_type", sa.String(96), nullable=False, index=True),
        sa.Column("schema_id", sa.String(255)),
        sa.Column("uri", sa.Text()),
        sa.Column("checksum_sha256", sa.String(64)),
        sa.Column("provenance_ref", sa.String(255)),
        sa.Column("metadata_json", sa.JSON(), nullable=False), *timestamps())
    sa.Table("snapshots", m,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("decision_id", sa.String(64), sa.ForeignKey("decisions.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("snapshot_type", sa.String(96), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("provenance_ref", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True))
    return m


def upgrade() -> None:
    _metadata().create_all(bind=op.get_bind())


def downgrade() -> None:
    _metadata().drop_all(bind=op.get_bind())
