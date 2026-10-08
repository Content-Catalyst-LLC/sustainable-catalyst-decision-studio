import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("SCDS_PERSISTENCE_REQUIRED", "false")
os.environ.setdefault("SCDS_PERSISTENCE_WRITE_ENABLED", "true")
os.environ.setdefault("SCDS_REPOSITORY_API_KEY", "test-repository-key")
os.environ["SCDS_GLOBAL_AUTH_JWT_SECRET"] = "v314-test-global-auth-secret"
os.environ["SCDS_GLOBAL_AUTH_ISSUER"] = "sustainable-catalyst-auth"
os.environ["SCDS_GLOBAL_AUTH_AUDIENCE"] = "decision-studio"
os.environ["SCDS_SERVICE_API_KEYS"] = json.dumps({
    "service-test-key": {"service_id": "service:test-runner", "scopes": ["rooms:read", "rooms:write", "repository:read"]}
})

from app.main import app
from app.global_auth import GLOBAL_AUTH_SCHEMA, AUTHENTICATED_PRINCIPAL_SCHEMA, global_auth_contract
from app.persistence.database import Base, EXPECTED_SCHEMA_REVISION
from app.persistence.repository import PersistenceRepository

ROOT = Path(__file__).resolve().parents[2]


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _jwt(sub: str, scopes, *, institution_id="inst:test", roles=None, exp_offset=3600, aud="decision-studio") -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "iss": "sustainable-catalyst-auth",
        "aud": aud,
        "sub": sub,
        "principal_type": "user",
        "institution_id": institution_id,
        "scopes": list(scopes),
        "roles": list(roles or []),
        "session_id": f"session:{sub}",
        "email": f"{sub.replace(':','-')}@example.test",
        "name": sub,
        "iat": now,
        "exp": now + exp_offset,
    }
    h64 = _b64(json.dumps(header, separators=(",", ":"), sort_keys=True).encode())
    p64 = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    sig = hmac.new(os.environ["SCDS_GLOBAL_AUTH_JWT_SECRET"].encode(), f"{h64}.{p64}".encode(), hashlib.sha256).digest()
    return f"{h64}.{p64}.{_b64(sig)}"


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _prepare_db(tmp_path):
    url = f"sqlite+pysqlite:///{tmp_path/'v3140.db'}"
    engine = create_engine(url, future=True)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"))
        conn.execute(text("DELETE FROM alembic_version"))
        conn.execute(text("INSERT INTO alembic_version(version_num) VALUES (:v)"), {"v": EXPECTED_SCHEMA_REVISION})
    os.environ["SCDS_DATABASE_URL"] = url
    os.environ["SCDS_PERSISTENCE_WRITE_ENABLED"] = "true"
    return engine


def test_global_auth_contract_and_release_boundary():
    c = global_auth_contract()
    assert c["schema"] == GLOBAL_AUTH_SCHEMA
    assert c["authentication_authority"] == "sustainable-catalyst-global-auth"
    assert c["primary_user_authentication"] == "bearer-jwt-hs256"
    assert c["legacy_api_key_status"] == "compatibility-only"
    assert c["principles"]["decision_room_membership_is_enforced_for_user_principals"] is True
    assert c["principles"]["request_body_cannot_impersonate_authenticated_room_actor"] is True
    assert c["schema_migration_required"] is False
    assert EXPECTED_SCHEMA_REVISION == "0003_v3150_event_ledger"
    assert len(Base.metadata.tables) == 27


def test_bearer_identity_and_scope_authorization():
    client = TestClient(app)
    token = _jwt("user:alice", ["canvas:read", "rooms:read"], roles=["researcher"])
    who = client.get("/auth/whoami", headers=_bearer(token))
    assert who.status_code == 200
    principal = who.json()["principal"]
    assert principal["schema"] == AUTHENTICATED_PRINCIPAL_SCHEMA
    assert principal["principal_id"] == "user:alice"
    assert principal["institution_id"] == "inst:test"
    assert principal["auth_method"] == "global-bearer-jwt"
    allowed = client.post("/auth/authorize", json={"required_scope": "canvas:read"}, headers=_bearer(token))
    assert allowed.status_code == 200 and allowed.json()["allowed"] is True
    denied = client.post("/auth/authorize", json={"required_scope": "canvas:write"}, headers=_bearer(token))
    assert denied.status_code == 403 and denied.json()["error"] == "insufficient_scope"


def test_invalid_bearer_never_downgrades_to_legacy_api_key():
    client = TestClient(app)
    headers = {"Authorization": "Bearer malformed.token.value", "X-SCDS-API-Key": "test-repository-key"}
    r = client.get("/auth/whoami", headers=headers)
    assert r.status_code == 401
    assert r.json()["error"] in {"invalid_bearer_token", "invalid_bearer_signature", "unsupported_bearer_token"}


def test_service_and_legacy_credentials_are_distinct():
    client = TestClient(app)
    service = client.get("/auth/whoami", headers={"X-SCDS-Service-Key": "service-test-key"})
    assert service.status_code == 200
    assert service.json()["principal"]["principal_id"] == "service:test-runner"
    assert service.json()["principal"]["legacy_compatibility"] is False
    legacy = client.get("/auth/whoami", headers={"X-SCDS-API-Key": "test-repository-key"})
    assert legacy.status_code == 200
    assert legacy.json()["principal"]["legacy_compatibility"] is True
    assert legacy.json()["principal"]["auth_method"] == "legacy-api-key"


def test_module_scope_accepts_global_bearer():
    client = TestClient(app)
    token = _jwt("user:canvas-reader", ["canvas:read"])
    r = client.get("/canvas/decisions/missing", headers=_bearer(token))
    # Authentication/authorization succeeded; repository lookup may be unavailable/not found.
    assert r.status_code != 403
    assert r.status_code != 401


def test_decision_room_membership_and_actor_spoofing(tmp_path):
    engine = _prepare_db(tmp_path)
    factory = sessionmaker(bind=engine, future=True)
    with factory() as session:
        repo = PersistenceRepository(session)
        repo.create_decision(decision_id="dec-auth-room", project_id=None, decision_question="Who may collaborate?")
        session.commit()

    client = TestClient(app)
    owner_token = _jwt("user:owner", ["rooms:read", "rooms:write"], institution_id="inst:alpha")
    reviewer_token = _jwt("user:reviewer", ["rooms:read", "rooms:write"], institution_id="inst:alpha")
    outsider_token = _jwt("user:outsider", ["rooms:read", "rooms:write"], institution_id="inst:alpha")

    create = client.post(
        "/decision-rooms/decisions/dec-auth-room",
        json={"title": "Auth room", "owner_ref": "user:spoofed", "actor_ref": "user:spoofed", "actor_role": "reviewer"},
        headers=_bearer(owner_token),
    )
    assert create.status_code == 200, create.text
    room = create.json()["decision_room"]
    room_id = room["room_id"]
    assert room["owner_ref"] == "user:owner"
    assert room["metadata"]["institution_id"] == "inst:alpha"

    add = client.post(
        f"/decision-rooms/{room_id}/members",
        json={"user_ref": "user:reviewer", "name": "Reviewer", "role": "reviewer", "actor_ref": "user:spoofed", "actor_role": "observer"},
        headers=_bearer(owner_token),
    )
    assert add.status_code == 200, add.text
    assert add.json()["member"]["invited_by"] == "user:owner"

    comment = client.post(
        f"/decision-rooms/{room_id}/comments",
        json={"author_ref": "user:owner", "author_role": "owner", "content": "Review note"},
        headers=_bearer(reviewer_token),
    )
    assert comment.status_code == 200, comment.text
    assert comment.json()["comment"]["author_ref"] == "user:reviewer"
    assert comment.json()["comment"]["author_role"] == "reviewer"

    outsider = client.get(f"/decision-rooms/{room_id}", headers=_bearer(outsider_token))
    assert outsider.status_code == 403
    assert outsider.json()["error"] == "decision_room_membership_required"

    access = client.get(f"/auth/decision-rooms/{room_id}/access", headers=_bearer(reviewer_token))
    assert access.status_code == 200
    assert access.json()["role"] == "reviewer"
    assert access.json()["membership_enforced"] is True

    os.environ.pop("SCDS_DATABASE_URL", None)


def test_v3140_route_inventory_file_if_present():
    path = ROOT / "data/backend_route_inventory_v3.14.0.json"
    if path.exists():
        inv = json.loads(path.read_text())
        assert inv["release"] == "3.14.0"
        assert inv["route_count"] == 300
        assert len(inv["routers"]["global_auth"]) == 7
