import os
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("SCDS_PERSISTENCE_REQUIRED", "false")
os.environ.setdefault("SCDS_PERSISTENCE_WRITE_ENABLED", "true")
os.environ.setdefault("SCDS_REPOSITORY_API_KEY", "test-repository-key")

from app.main import app
from app.decision_rooms import (
    DECISION_ROOM_SCHEMA,
    DECISION_ROOM_EVENT_SCHEMA,
    DECISION_ROOM_PERSISTENCE_SCHEMA,
    DecisionRoomRepository,
    DecisionRoomUpsertRequest,
    DecisionRoomPatchRequest,
    DecisionRoomImportRequest,
    RoomMemberCreateRequest,
    RoomCommentCreateRequest,
    RoomCommentPatchRequest,
    RoomChangeRequestCreate,
    RoomChangeRequestPatch,
    RoomSnapshotCreateRequest,
    RoomShareGrantCreateRequest,
    decision_room_contract,
    decision_room_template,
    validate_decision_room,
)
from app.persistence.database import Base, EXPECTED_SCHEMA_REVISION, PERSISTENCE_TABLES
from app.persistence.models import DecisionRoomShareGrant
from app.persistence.repository import PersistenceRepository

ROOT = Path(__file__).resolve().parents[2]


def _session(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path/'v3130.db'}", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def test_contract_schema_and_migration_boundary():
    c=decision_room_contract()
    assert c["schema"] == DECISION_ROOM_SCHEMA
    assert c["event_schema"] == DECISION_ROOM_EVENT_SCHEMA
    assert c["persistence_schema"] == DECISION_ROOM_PERSISTENCE_SCHEMA
    assert c["storage_authority"] == "python-postgresql"
    assert c["principles"]["wordpress_is_not_canonical_room_persistence"] is True
    assert c["principles"]["room_events_are_hash_chained"] is True
    assert c["principles"]["ai_cannot_approve_or_sign"] is True
    assert EXPECTED_SCHEMA_REVISION == "0002_v3130_collaboration"
    assert len(PERSISTENCE_TABLES) == 26
    for t in ["decision_rooms","decision_room_members","decision_room_comments","decision_room_change_requests","decision_room_share_grants","decision_room_events"]:
        assert t in PERSISTENCE_TABLES
    template=decision_room_template("dec-1")
    assert template["canonical_persistence"] == "python-postgresql"
    assert validate_decision_room(template)["ok"] is True


def test_room_member_comment_change_snapshot_and_hash_chain(tmp_path):
    session=_session(tmp_path)
    repo=PersistenceRepository(session)
    repo.create_decision(decision_id="dec-room", project_id=None, decision_question="Collaborate?")
    rooms=DecisionRoomRepository(session, app_version="3.13.0")
    room=rooms.upsert_for_decision("dec-room", DecisionRoomUpsertRequest(title="Review room", owner_ref="user:owner", actor_ref="user:owner", actor_role="owner"))
    rid=room["room_id"]
    assert room["canonical_persistence"] == "python-postgresql"
    member=rooms.add_member(rid, RoomMemberCreateRequest(name="Reviewer", user_ref="user:reviewer", role="reviewer", actor_ref="user:owner", actor_role="owner"))
    assert member["role"] == "reviewer"
    comment=rooms.add_comment(rid, RoomCommentCreateRequest(author_ref="user:reviewer", author_role="reviewer", content="Please document this assumption."))
    assert comment["status"] == "open"
    resolved=rooms.patch_comment(rid, comment["comment_id"], RoomCommentPatchRequest(resolved_by="user:reviewer", actor_role="reviewer", resolution="Addressed."))
    assert resolved["status"] == "resolved"
    change=rooms.add_change_request(rid, RoomChangeRequestCreate(requested_by="user:reviewer", requester_role="reviewer", summary="Revise evidence wording", packet_patch={"summary":"revised"}))
    assert change["status"] == "open"
    change2=rooms.patch_change_request(rid, change["change_request_id"], RoomChangeRequestPatch(resolved_by="user:reviewer", actor_role="reviewer", resolution="Accepted"))
    assert change2["status"] == "resolved"
    snap=rooms.create_snapshot(rid, RoomSnapshotCreateRequest(payload={"decision":"state"}, actor_ref="user:reviewer", actor_role="reviewer"))
    assert len(snap["content_sha256"]) == 64
    history=rooms.events(rid)
    assert history["integrity"]["ok"] is True
    assert history["integrity"]["event_count"] >= 7
    assert history["events"][0]["previous_hash"] == "GENESIS"
    assert history["integrity"]["head_hash"] == rooms.get(rid)["head_event_hash"]
    session.close()


def test_share_token_is_hash_only(tmp_path):
    session=_session(tmp_path)
    PersistenceRepository(session).create_decision(decision_id="dec-share-room", project_id=None, decision_question="Share room?")
    rooms=DecisionRoomRepository(session, app_version="3.13.0")
    rid=rooms.upsert_for_decision("dec-share-room", DecisionRoomUpsertRequest(actor_ref="owner", actor_role="owner"))["room_id"]
    grant, token=rooms.create_share_grant(rid, RoomShareGrantCreateRequest(role="reviewer", actor_ref="owner", actor_role="owner"))
    row=session.get(DecisionRoomShareGrant, grant["grant_id"])
    assert row is not None
    assert token not in row.token_hash
    assert len(row.token_hash) == 64
    assert grant["token_hint"] and token not in grant["token_hint"]
    assert "token_hash" not in grant
    session.close()


def test_legacy_wordpress_room_import_is_source_preserving_and_idempotent(tmp_path):
    session=_session(tmp_path)
    PersistenceRepository(session).create_decision(decision_id="dec-import-room", project_id=None, decision_question="Import?")
    rooms=DecisionRoomRepository(session, app_version="3.13.0")
    legacy={
        "schema":"scds-collaborative-decision-room/1.0","room_id":"room-legacy","title":"Legacy room","visibility":"private","status":"active",
        "owner":{"name":"Legacy Owner"},
        "members":[{"member_id":"legacy-member","user_id":"u1","name":"Legacy Reviewer","role":"reviewer","status":"active"}],
        "comments":[{"comment_id":"legacy-comment","author":"Legacy Reviewer","author_role":"reviewer","content":"Legacy comment","status":"open"}],
    }
    first=rooms.import_legacy(DecisionRoomImportRequest(decision_id="dec-import-room", room=legacy, actor_ref="migration:operator"))
    second=rooms.import_legacy(DecisionRoomImportRequest(decision_id="dec-import-room", room=legacy, actor_ref="migration:operator"))
    assert first["room"]["room_id"] == "room-legacy"
    assert second["idempotent"] is True
    assert len(rooms.members("room-legacy")) == 1
    assert len(rooms.comments("room-legacy")) == 1
    assert rooms.get("room-legacy")["metadata"]["legacy_wordpress_source_preserved"] is True
    session.close()


def test_api_contract_and_auth():
    client=TestClient(app)
    c=client.get('/decision-rooms/contract')
    assert c.status_code == 200
    assert c.json()['version'] == '3.14.0'
    assert c.json()['decision_room_contract']['schema'] == DECISION_ROOM_SCHEMA
    denied=client.get('/decision-rooms/does-not-exist')
    assert denied.status_code == 403


def test_v3130_route_inventory_file_if_present():
    path=ROOT/'data/backend_route_inventory_v3.13.0.json'
    if path.exists():
        import json
        inv=json.loads(path.read_text())
        assert inv['release']=='3.13.0'
        assert inv['route_count']==293
        assert len(inv['routers']['decision_rooms'])==21
