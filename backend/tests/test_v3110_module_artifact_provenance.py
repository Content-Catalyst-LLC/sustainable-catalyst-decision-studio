import os
from pathlib import Path

from fastapi.testclient import TestClient

os.environ.setdefault("SCDS_PERSISTENCE_REQUIRED", "false")
os.environ.setdefault("SCDS_PERSISTENCE_WRITE_ENABLED", "true")
os.environ.setdefault("SCDS_REPOSITORY_API_KEY", "test-repository-key")

from app.main import app
from app.module_artifact_provenance import (
    MODULE_ARTIFACT_SCHEMA,
    MODULE_PROVENANCE_SCHEMA,
    ModuleArtifactCreateRequest,
    ModuleArtifactRepository,
    ModuleArtifactRevisionRequest,
    module_artifact_contract,
    module_artifact_template,
    validate_module_artifact,
)
from app.persistence.database import Base
from app.persistence.repository import PersistenceRepository
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]


def _session(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path/'v3110.db'}", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def test_contract_and_template_boundaries():
    c = module_artifact_contract()
    assert c["schema"] == MODULE_ARTIFACT_SCHEMA
    assert c["provenance_schema"] == MODULE_PROVENANCE_SCHEMA
    assert c["persistence"]["schema_migration_required"] is False
    assert c["principles"]["artifact_revisions_are_immutable"] is True
    assert c["principles"]["provenance_does_not_imply_truth"] is True
    assert c["compute_authorities"] == {"finance": "workbench", "global-impact": "workbench"}
    t = module_artifact_template("dec-1", "finance")
    assert t["module_id"] == "finance"
    assert t["ownership"]["final_decision_authority"] == "human-governed"


def test_immutable_revisions_integrity_and_lineage(tmp_path):
    session = _session(tmp_path)
    repo = PersistenceRepository(session)
    repo.create_decision(decision_id="dec-art", project_id=None, decision_question="Artifact test")
    mar = ModuleArtifactRepository(session, app_version="3.11.0")
    first = mar.create("dec-art", ModuleArtifactCreateRequest(
        module_id="finance", artifact_type="valuation-context", title="DCF context",
        payload={"discount_rate": 0.08}, evidence_refs=["evidence:1"], computation_refs=["workbench:run-1"],
        provenance={"methodology":"Workbench result receipt preserved"},
    ))
    assert first["revision_no"] == 1
    assert len(first["integrity"]["content_sha256"]) == 64
    assert validate_module_artifact(first)["ok"] is True
    second = mar.revise("dec-art", first["artifact_id"], ModuleArtifactRevisionRequest(
        module_id="finance", payload={"discount_rate": 0.09}, computation_refs=["workbench:run-2"]
    ))
    assert second["revision_no"] == 2
    assert second["revision_id"] != first["revision_id"]
    assert first["revision_id"] in second["parent_artifact_ids"]
    assert mar.get("dec-art", first["revision_id"])["payload"]["discount_rate"] == 0.08
    assert mar.get("dec-art", first["artifact_id"])["payload"]["discount_rate"] == 0.09
    lineage = mar.lineage("dec-art", first["artifact_id"])
    assert lineage["revision_count"] == 2
    assert lineage["current_revision_no"] == 2
    assert lineage["boundaries"]["lineage_implies_truth"] is False
    session.commit(); session.close()


def test_module_ownership_cannot_change(tmp_path):
    session = _session(tmp_path)
    repo = PersistenceRepository(session)
    repo.create_decision(decision_id="dec-own", project_id=None, decision_question="Ownership")
    mar = ModuleArtifactRepository(session, app_version="3.11.0")
    first = mar.create("dec-own", ModuleArtifactCreateRequest(module_id="canvas", artifact_type="framing", payload={"x":1}))
    try:
        mar.revise("dec-own", first["artifact_id"], ModuleArtifactRevisionRequest(module_id="finance", payload={"x":2}))
        assert False, "expected ownership error"
    except ValueError as exc:
        assert str(exc) == "module_ownership_change_prohibited"
    session.close()


def test_api_contract_and_auth():
    client = TestClient(app)
    c = client.get('/module-artifacts/contract')
    assert c.status_code == 200
    assert c.json()['version'] == '3.11.0'
    assert c.json()['module_artifact_contract']['schema'] == MODULE_ARTIFACT_SCHEMA
    denied = client.get('/module-artifacts/decisions/does-not-exist')
    assert denied.status_code == 403


def test_v3110_route_inventory_file_exists():
    path = ROOT / 'data/backend_route_inventory_v3.11.0.json'
    if path.exists():
        import json
        inv = json.loads(path.read_text())
        assert inv['release'] == '3.11.0'
        assert inv['route_count'] == 264
