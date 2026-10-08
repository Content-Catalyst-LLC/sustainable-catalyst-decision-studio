import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text, update, delete
from sqlalchemy.exc import DatabaseError, IntegrityError
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("SCDS_PERSISTENCE_REQUIRED", "false")
os.environ.setdefault("SCDS_PERSISTENCE_WRITE_ENABLED", "true")
os.environ.setdefault("SCDS_REPOSITORY_API_KEY", "test-repository-key")

from app.main import app
from app.audit_ledger import (
    AUDIT_EVENT_SCHEMA,
    DECISION_EVENT_STORE_SCHEMA,
    IMMUTABLE_AUDIT_LEDGER_SCHEMA,
    DecisionAuditLedgerRepository,
    audit_ledger_contract,
)
from app.persistence.database import Base, EXPECTED_SCHEMA_REVISION, PERSISTENCE_TABLES
from app.persistence.models import DecisionAuditEvent
from app.persistence.repository import PersistenceRepository

ROOT = Path(__file__).resolve().parents[2]


def _session(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path/'v3150.db'}", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def test_contract_and_schema_boundary():
    c = audit_ledger_contract()
    assert c["schema"] == IMMUTABLE_AUDIT_LEDGER_SCHEMA
    assert c["event_store_schema"] == DECISION_EVENT_STORE_SCHEMA
    assert c["event_schema"] == AUDIT_EVENT_SCHEMA
    assert c["principles"]["append_only"] is True
    assert c["principles"]["database_mutation_guard"] is True
    assert c["principles"]["replay_does_not_reexecute_domain_mutations"] is True
    assert c["final_decision_authority"] == "human-governed"
    assert EXPECTED_SCHEMA_REVISION == "0003_v3150_event_ledger"
    assert len(PERSISTENCE_TABLES) == 27
    assert "decision_audit_events" in PERSISTENCE_TABLES


def test_repository_dual_writes_hash_chained_ledger(tmp_path):
    session = _session(tmp_path)
    repo = PersistenceRepository(session)
    repo.create_decision(decision_id="dec-audit", project_id=None, decision_question="Audit this?")
    repo.update_decision("dec-audit", {"lifecycle_state": "analysis"})
    ledger = DecisionAuditLedgerRepository(session)
    events = ledger.list("dec-audit")
    assert [e["event_type"] for e in events[:2]] == ["decision.created", "decision.updated"]
    assert events[0]["previous_event_hash"] == "GENESIS"
    assert events[1]["previous_event_hash"] == events[0]["event_hash"]
    assert len(events[0]["payload_hash"]) == 64
    assert ledger.verify("dec-audit")["ok"] is True
    replay = ledger.replay("dec-audit")
    assert replay["mode"] == "read-only-audit-replay"
    assert replay["reexecutes_domain_mutations"] is False
    assert len(replay["replay_digest_sha256"]) == 64
    session.close()


def test_actor_identity_and_explicit_metadata(tmp_path):
    session = _session(tmp_path)
    repo = PersistenceRepository(session)
    repo.create_decision(decision_id="dec-actor", project_id=None, decision_question="Actor?")
    event = DecisionAuditLedgerRepository(session).append(
        decision_id="dec-actor", event_type="decision.disposition.recorded", payload={"disposition":"approved-by-human"},
        actor_ref="user:reviewer", actor_type="user", institution_id="inst:1", authentication_method="global-bearer-jwt",
        object_type="decision", object_id="dec-actor", correlation_id="corr-1", causation_id="cause-1",
        provenance_refs=["prov:1"],
    )
    assert event["actor"]["subject"] == "user:reviewer"
    assert event["actor"]["institution_id"] == "inst:1"
    assert event["correlation_id"] == "corr-1"
    assert event["causation_id"] == "cause-1"
    session.close()


def test_legacy_decision_events_backfill_is_idempotent(tmp_path):
    session = _session(tmp_path)
    repo = PersistenceRepository(session)
    repo.create_decision(decision_id="dec-backfill", project_id=None, decision_question="Backfill?")
    # Simulate a brand-new ledger migration by removing the dual-written ledger rows in this metadata-only unit setup.
    session.execute(delete(DecisionAuditEvent).where(DecisionAuditEvent.decision_id == "dec-backfill"))
    session.commit()
    ledger = DecisionAuditLedgerRepository(session)
    first = ledger.backfill_legacy_events(decision_id="dec-backfill")
    second = ledger.backfill_legacy_events(decision_id="dec-backfill")
    assert first["imported"] == 1
    assert second["imported"] == 0 and second["skipped"] == 1
    assert ledger.verify("dec-backfill")["ok"] is True
    session.close()


def test_alembic_migration_creates_append_only_trigger(tmp_path):
    from alembic import command
    from alembic.config import Config
    db = tmp_path / "migrate3150.db"
    cfg = Config(str(ROOT / "backend/alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "backend/migrations"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db}")
    command.upgrade(cfg, "head")
    engine = create_engine(f"sqlite:///{db}", future=True)
    with engine.begin() as conn:
        revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        tables = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
    assert revision == "0003_v3150_event_ledger"
    assert "decision_audit_events" in tables
    # Insert minimal parent + event and prove UPDATE/DELETE are blocked by trigger.
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO decisions(id, decision_question, lifecycle_state, final_decision_authority, metadata_json, created_at, updated_at) VALUES ('d1','q','framing','human-governed','{}',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        conn.execute(text("""INSERT INTO decision_audit_events(id,stream_id,decision_id,sequence_no,event_type,event_payload,payload_hash,provenance_refs,previous_event_hash,event_hash,occurred_at,metadata_json) VALUES ('e1','decision:d1','d1',1,'decision.created','{}',:h,'[]','GENESIS',:eh,CURRENT_TIMESTAMP,'{}')"""), {"h":"a"*64,"eh":"b"*64})
    with pytest.raises(Exception):
        with engine.begin() as conn:
            conn.execute(text("UPDATE decision_audit_events SET event_type='changed' WHERE id='e1'"))
    with pytest.raises(Exception):
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM decision_audit_events WHERE id='e1'"))


def test_api_contract_auth_and_route_inventory_if_present():
    client = TestClient(app)
    c = client.get('/audit-ledger/contract')
    assert c.status_code == 200
    assert c.json()['version'] == '3.15.0'
    assert c.json()['audit_ledger_contract']['schema'] == IMMUTABLE_AUDIT_LEDGER_SCHEMA
    denied = client.get('/audit-ledger/decisions/missing')
    assert denied.status_code == 403
    path = ROOT/'data/backend_route_inventory_v3.15.0.json'
    if path.exists():
        import json
        inv=json.loads(path.read_text())
        assert inv['release']=='3.15.0'
        assert len(inv['routers']['audit_ledger'])==8
