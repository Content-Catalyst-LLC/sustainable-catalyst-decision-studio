import os
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("SCDS_PERSISTENCE_REQUIRED", "false")
os.environ.setdefault("SCDS_PERSISTENCE_WRITE_ENABLED", "true")
os.environ.setdefault("SCDS_REPOSITORY_API_KEY", "test-repository-key")

from app.main import app
from app.module_interoperability import (
    MODULE_INTEROPERABILITY_SCHEMA,
    SHARED_EVIDENCE_SCHEMA,
    ArtifactLink,
    ContradictionAnnotation,
    ModuleInteroperabilityRepository,
    ModuleInteroperabilityUpsertRequest,
    SharedEvidenceReference,
    SharedEvidenceShareRequest,
    SharedEvidenceUsage,
    module_interoperability_contract,
    module_interoperability_template,
    validate_module_interoperability,
)
from app.persistence.database import Base
from app.persistence.models import EvidenceLink
from app.persistence.repository import PersistenceRepository

ROOT = Path(__file__).resolve().parents[2]


def _session(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path/'v3120.db'}", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def test_contract_and_template_boundaries():
    c = module_interoperability_contract()
    assert c["schema"] == MODULE_INTEROPERABILITY_SCHEMA
    assert c["shared_evidence_schema"] == SHARED_EVIDENCE_SCHEMA
    assert c["persistence"]["schema_migration_required"] is False
    assert c["principles"]["evidence_payload_is_not_duplicated"] is True
    assert c["principles"]["owner_module_is_preserved"] is True
    assert c["principles"]["contradictions_are_visible_not_silently_reconciled"] is True
    t = module_interoperability_template("dec-1")
    assert t["decision_id"] == "dec-1"
    assert t["boundaries"]["truth_is_automatically_verified"] is False
    assert t["boundaries"]["final_decision_authority"] == "human-governed"


def test_shared_evidence_reuse_and_usage_edges(tmp_path):
    session = _session(tmp_path)
    repo = PersistenceRepository(session)
    repo.create_decision(decision_id="dec-share", project_id=None, decision_question="Shared evidence?")
    interop = ModuleInteroperabilityRepository(session, app_version="3.12.0")
    doc = interop.upsert("dec-share", ModuleInteroperabilityUpsertRequest(
        shared_evidence=[SharedEvidenceReference(
            evidence_ref="core:evidence:123",
            owner_module="canvas",
            source_ref="library:source:abc",
            source_provenance_ref="core:prov:abc",
            usages=[
                SharedEvidenceUsage(module_id="canvas", relation="supports", purpose="Problem framing", claim_ref="claim:cost"),
                SharedEvidenceUsage(module_id="finance", relation="supports", purpose="Cost assumption", claim_ref="claim:cost"),
                SharedEvidenceUsage(module_id="global-impact", relation="contextualizes", purpose="Distributional context"),
            ],
        )],
        artifact_links=[ArtifactLink(artifact_ref="ma:finance:1", owner_module="finance", consumer_modules=["canvas"], relationship="informs")],
    ))
    assert doc["shared_evidence"][0]["evidence_ref"] == "core:evidence:123"
    assert doc["shared_evidence"][0]["owner_module"] == "canvas"
    assert set(doc["shared_evidence"][0]["consumer_modules"]) == {"canvas", "finance", "global-impact"}
    assert "payload" not in doc["shared_evidence"][0]
    links = list(session.scalars(select(EvidenceLink).where(EvidenceLink.decision_id == "dec-share")))
    assert len(links) == 3
    assert all((x.metadata_json or {}).get("domain") == "module-interoperability" for x in links)
    assert all((x.metadata_json or {}).get("ownership_transfer") is False for x in links)
    assert validate_module_interoperability(doc)["ok"] is True
    session.commit(); session.close()


def test_share_preserves_owner_and_adds_consumer(tmp_path):
    session = _session(tmp_path)
    repo = PersistenceRepository(session)
    repo.create_decision(decision_id="dec-share2", project_id=None, decision_question="Reuse?")
    interop = ModuleInteroperabilityRepository(session, app_version="3.12.0")
    first = interop.share("dec-share2", SharedEvidenceShareRequest(
        evidence_ref="core:evidence:1", owner_module="narrative-risk",
        usage=SharedEvidenceUsage(module_id="narrative-risk", relation="supports", purpose="Risk claim"),
    ))
    second = interop.share("dec-share2", SharedEvidenceShareRequest(
        evidence_ref="core:evidence:1", owner_module="narrative-risk",
        usage=SharedEvidenceUsage(module_id="finance", relation="qualifies", purpose="Risk-adjusted assumption"),
    ))
    item = second["shared_evidence"][0]
    assert item["owner_module"] == "narrative-risk"
    assert set(item["consumer_modules"]) == {"narrative-risk", "finance"}
    try:
        interop.share("dec-share2", SharedEvidenceShareRequest(
            evidence_ref="core:evidence:1", owner_module="finance",
            usage=SharedEvidenceUsage(module_id="finance", relation="supports"),
        ))
        assert False, "expected owner change rejection"
    except ValueError as exc:
        assert str(exc) == "evidence_owner_change_prohibited"
    session.close()


def test_contradiction_visibility_without_truth_adjudication(tmp_path):
    session = _session(tmp_path)
    repo = PersistenceRepository(session)
    repo.create_decision(decision_id="dec-contr", project_id=None, decision_question="Conflicting interpretation?")
    interop = ModuleInteroperabilityRepository(session, app_version="3.12.0")
    doc = interop.upsert("dec-contr", ModuleInteroperabilityUpsertRequest(
        shared_evidence=[SharedEvidenceReference(
            evidence_ref="core:evidence:conflict", owner_module="canvas",
            usages=[
                SharedEvidenceUsage(module_id="finance", relation="supports", claim_ref="claim:1"),
                SharedEvidenceUsage(module_id="narrative-risk", relation="refutes", claim_ref="claim:1"),
            ],
        )],
        contradiction_annotations=[ContradictionAnnotation(
            evidence_refs=["core:evidence:conflict"], module_ids=["finance", "narrative-risk"],
            statement="Modules interpret the same evidence differently.",
        )],
    ))
    diag = interop.diagnostics("dec-contr")
    assert diag["explicit_contradiction_count"] == 1
    assert diag["relation_disagreement_count"] == 1
    assert diag["boundaries"]["relation_disagreement_is_not_truth_adjudication"] is True
    assert doc["boundaries"]["contradiction_is_automatically_resolved"] is False
    session.close()


def test_existing_non_interoperability_evidence_links_survive(tmp_path):
    session = _session(tmp_path)
    repo = PersistenceRepository(session)
    repo.create_decision(decision_id="dec-isolate", project_id=None, decision_question="Isolation?")
    session.add(EvidenceLink(id="nr-link", decision_id="dec-isolate", claim_id=None, evidence_ref="nr:e1", relation="supports", metadata_json={"domain":"narrative-risk"}))
    session.flush()
    interop = ModuleInteroperabilityRepository(session, app_version="3.12.0")
    interop.upsert("dec-isolate", ModuleInteroperabilityUpsertRequest(shared_evidence=[SharedEvidenceReference(
        evidence_ref="core:evidence:x", owner_module="global-impact", usages=[SharedEvidenceUsage(module_id="finance", relation="informs")]
    )]))
    interop.upsert("dec-isolate", ModuleInteroperabilityUpsertRequest(shared_evidence=[]))
    assert session.get(EvidenceLink, "nr-link") is not None
    session.close()


def test_api_contract_and_auth():
    client = TestClient(app)
    c = client.get('/module-interoperability/contract')
    assert c.status_code == 200
    assert c.json()['version'] == '3.14.0'
    assert c.json()['module_interoperability_contract']['schema'] == MODULE_INTEROPERABILITY_SCHEMA
    denied = client.get('/module-interoperability/decisions/does-not-exist')
    assert denied.status_code == 403


def test_v3120_route_inventory_file_exists():
    path = ROOT / 'data/backend_route_inventory_v3.12.0.json'
    if path.exists():
        import json
        inv = json.loads(path.read_text())
        assert inv['release'] == '3.12.0'
        assert inv['route_count'] == 272
