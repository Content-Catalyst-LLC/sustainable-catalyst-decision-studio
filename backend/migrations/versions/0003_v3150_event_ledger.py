"""Decision Studio v3.15.0 immutable decision event store and audit ledger.

Revision ID: 0003_v3150_event_ledger
Revises: 0002_v3130_collaboration
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0003_v3150_event_ledger"
down_revision = "0002_v3130_collaboration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decision_audit_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("stream_id", sa.String(96), nullable=False),
        sa.Column("decision_id", sa.String(64), sa.ForeignKey("decisions.id", ondelete="CASCADE")),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(160), nullable=False),
        sa.Column("actor_subject", sa.String(255)),
        sa.Column("actor_type", sa.String(64)),
        sa.Column("institution_id", sa.String(255)),
        sa.Column("authentication_method", sa.String(96)),
        sa.Column("module_id", sa.String(64)),
        sa.Column("object_type", sa.String(96)),
        sa.Column("object_id", sa.String(255)),
        sa.Column("correlation_id", sa.String(128)),
        sa.Column("causation_id", sa.String(128)),
        sa.Column("event_payload", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("provenance_refs", sa.JSON(), nullable=False),
        sa.Column("previous_event_hash", sa.String(64), nullable=False),
        sa.Column("event_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("stream_id", "sequence_no", name="uq_decision_audit_event_stream_sequence"),
    )
    for col in ["stream_id","decision_id","event_type","actor_subject","institution_id","module_id","object_type","object_id","correlation_id","causation_id","occurred_at"]:
        op.create_index(f"ix_decision_audit_events_{col}", "decision_audit_events", [col])
    op.create_index("ix_decision_audit_events_decision_sequence", "decision_audit_events", ["decision_id", "sequence_no"])

    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.execute("""
        CREATE OR REPLACE FUNCTION scds_block_audit_event_mutation()
        RETURNS trigger AS $$
        BEGIN
          IF current_setting('scds.audit_maintenance', true) = 'on' THEN
            RETURN OLD;
          END IF;
          RAISE EXCEPTION 'decision_audit_events is append-only';
        END;
        $$ LANGUAGE plpgsql;
        """)
        op.execute("""
        CREATE TRIGGER trg_decision_audit_events_no_update
        BEFORE UPDATE ON decision_audit_events
        FOR EACH ROW EXECUTE FUNCTION scds_block_audit_event_mutation();
        """)
        op.execute("""
        CREATE TRIGGER trg_decision_audit_events_no_delete
        BEFORE DELETE ON decision_audit_events
        FOR EACH ROW EXECUTE FUNCTION scds_block_audit_event_mutation();
        """)
    elif dialect == "sqlite":
        op.execute("""
        CREATE TRIGGER trg_decision_audit_events_no_update
        BEFORE UPDATE ON decision_audit_events
        BEGIN SELECT RAISE(ABORT, 'decision_audit_events is append-only'); END;
        """)
        op.execute("""
        CREATE TRIGGER trg_decision_audit_events_no_delete
        BEFORE DELETE ON decision_audit_events
        BEGIN SELECT RAISE(ABORT, 'decision_audit_events is append-only'); END;
        """)


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_decision_audit_events_no_update ON decision_audit_events")
        op.execute("DROP TRIGGER IF EXISTS trg_decision_audit_events_no_delete ON decision_audit_events")
        op.execute("DROP FUNCTION IF EXISTS scds_block_audit_event_mutation()")
    elif dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS trg_decision_audit_events_no_update")
        op.execute("DROP TRIGGER IF EXISTS trg_decision_audit_events_no_delete")
    op.drop_table("decision_audit_events")
