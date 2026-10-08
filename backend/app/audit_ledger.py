from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.global_auth import current_auth_principal
from app.persistence.database import session_scope
from app.persistence.models import Decision, DecisionAuditEvent, DecisionEvent

DECISION_EVENT_STORE_SCHEMA = "scds-decision-event-store/1.0"
IMMUTABLE_AUDIT_LEDGER_SCHEMA = "scds-immutable-audit-ledger/1.0"
AUDIT_EVENT_SCHEMA = "scds-decision-audit-event/1.0"
AUDIT_LEDGER_VERSION = "1.0"
GENESIS_HASH = "GENESIS"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _hash(value: Any) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _id() -> str:
    return f"audit_evt_{uuid4().hex[:22]}"


def _infer_module(event_type: str) -> str | None:
    prefix = event_type.split(".", 1)[0]
    return {
        "canvas": "canvas",
        "finance": "finance",
        "narrative_risk": "narrative-risk",
        "global_impact": "global-impact",
        "decision_composition": "composition",
        "module_artifact": "artifacts",
        "module_interoperability": "interoperability",
        "decision_room": "decision-room",
    }.get(prefix)


class AuditEventAppendRequest(BaseModel):
    event_type: str = Field(min_length=3, max_length=160)
    payload: dict[str, Any] = Field(default_factory=dict)
    module_id: str | None = None
    object_type: str | None = None
    object_id: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    provenance_refs: list[Any] = Field(default_factory=list)


class AuditEventValidateRequest(BaseModel):
    event: dict[str, Any]
    strict: bool = True


def audit_ledger_contract() -> dict[str, Any]:
    return {
        "schema": IMMUTABLE_AUDIT_LEDGER_SCHEMA,
        "event_store_schema": DECISION_EVENT_STORE_SCHEMA,
        "event_schema": AUDIT_EVENT_SCHEMA,
        "version": AUDIT_LEDGER_VERSION,
        "role": "canonical-append-only-cross-module-decision-audit-history",
        "storage_authority": "python-postgresql",
        "identity_authority": "sustainable-catalyst-global-auth",
        "table": "decision_audit_events",
        "migration_revision": "0003_v3150_event_ledger",
        "principles": {
            "append_only": True,
            "database_mutation_guard": True,
            "deterministic_sequence_per_stream": True,
            "sha256_payload_fingerprint": True,
            "sha256_hash_chain": True,
            "authenticated_actor_identity_is_recorded": True,
            "institution_identity_is_recorded_when_available": True,
            "correlation_and_causation_are_explicit": True,
            "historical_decision_events_are_backfillable": True,
            "replay_is_read_only": True,
            "replay_does_not_reexecute_domain_mutations": True,
            "audit_integrity_does_not_imply_truth": True,
            "audit_integrity_does_not_imply_causality": True,
            "audit_event_does_not_imply_approval": True,
        },
        "covered_event_families": [
            "decision.*", "decision_module.*", "canvas.*", "finance.*",
            "narrative_risk.*", "global_impact.*", "decision_composition.*",
            "module_artifact.*", "module_interoperability.*", "decision_room.*",
        ],
        "final_decision_authority": "human-governed",
    }


def audit_event_template(decision_id: str = "") -> dict[str, Any]:
    return {
        "schema": AUDIT_EVENT_SCHEMA,
        "event_id": "",
        "stream_id": f"decision:{decision_id}" if decision_id else "decision:<id>",
        "decision_id": decision_id,
        "sequence_no": 1,
        "event_type": "decision.updated",
        "actor": {"subject": None, "type": None, "institution_id": None, "authentication_method": None},
        "module_id": None,
        "object_type": None,
        "object_id": None,
        "correlation_id": None,
        "causation_id": None,
        "payload": {},
        "payload_hash": "",
        "provenance_refs": [],
        "previous_event_hash": GENESIS_HASH,
        "event_hash": "",
        "occurred_at": None,
    }


def validate_audit_event(event: dict[str, Any], *, strict: bool = True) -> dict[str, Any]:
    required = ["schema", "event_id", "stream_id", "sequence_no", "event_type", "payload_hash", "previous_event_hash", "event_hash", "occurred_at"]
    errors = [f"missing:{key}" for key in required if event.get(key) in (None, "")]
    if event.get("schema") not in (None, AUDIT_EVENT_SCHEMA):
        errors.append("invalid_schema")
    if strict and event.get("sequence_no") is not None and int(event.get("sequence_no", 0)) < 1:
        errors.append("invalid_sequence")
    for key in ("payload_hash", "event_hash"):
        value = str(event.get(key) or "")
        if value and (len(value) != 64 or any(c not in "0123456789abcdef" for c in value.lower())):
            errors.append(f"invalid_{key}")
    return {"ok": not errors, "schema": AUDIT_EVENT_SCHEMA, "errors": errors}


class DecisionAuditLedgerRepository:
    def __init__(self, session: Session):
        self.session = session

    def _stream_lock(self, stream_id: str) -> None:
        bind = self.session.get_bind()
        if bind is not None and bind.dialect.name == "postgresql":
            self.session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:stream_id))"), {"stream_id": stream_id})

    @staticmethod
    def _row_dict(row: DecisionAuditEvent) -> dict[str, Any]:
        return {
            "schema": AUDIT_EVENT_SCHEMA,
            "event_id": row.id,
            "stream_id": row.stream_id,
            "decision_id": row.decision_id,
            "sequence_no": row.sequence_no,
            "event_type": row.event_type,
            "actor": {
                "subject": row.actor_subject,
                "type": row.actor_type,
                "institution_id": row.institution_id,
                "authentication_method": row.authentication_method,
            },
            "module_id": row.module_id,
            "object_type": row.object_type,
            "object_id": row.object_id,
            "correlation_id": row.correlation_id,
            "causation_id": row.causation_id,
            "payload": row.event_payload or {},
            "payload_hash": row.payload_hash,
            "provenance_refs": row.provenance_refs or [],
            "previous_event_hash": row.previous_event_hash,
            "event_hash": row.event_hash,
            "occurred_at": _iso(row.occurred_at),
            "metadata": row.metadata_json or {},
        }

    def append(
        self,
        *,
        decision_id: str | None,
        event_type: str,
        payload: dict[str, Any] | None = None,
        actor_ref: str | None = None,
        actor_type: str | None = None,
        institution_id: str | None = None,
        authentication_method: str | None = None,
        module_id: str | None = None,
        object_type: str | None = None,
        object_id: str | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        provenance_refs: list[Any] | None = None,
        occurred_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
        stream_id: str | None = None,
    ) -> dict[str, Any]:
        if decision_id and self.session.get(Decision, decision_id) is None:
            raise LookupError("decision_not_found")
        stream = stream_id or (f"decision:{decision_id}" if decision_id else "system")
        self._stream_lock(stream)
        last = self.session.scalar(
            select(DecisionAuditEvent)
            .where(DecisionAuditEvent.stream_id == stream)
            .order_by(DecisionAuditEvent.sequence_no.desc())
            .limit(1)
        )
        sequence = int(last.sequence_no if last else 0) + 1
        previous = last.event_hash if last else GENESIS_HASH
        principal = current_auth_principal()
        actor_subject = principal.principal_id if principal else actor_ref
        resolved_actor_type = principal.principal_type if principal else actor_type
        resolved_institution = principal.institution_id if principal else institution_id
        resolved_auth = principal.auth_method if principal else authentication_method
        body_payload = payload or {}
        payload_hash = _hash(body_payload)
        when = occurred_at or _now()
        event_body = {
            "schema": AUDIT_EVENT_SCHEMA,
            "stream_id": stream,
            "decision_id": decision_id,
            "sequence_no": sequence,
            "event_type": event_type,
            "actor_subject": actor_subject,
            "actor_type": resolved_actor_type,
            "institution_id": resolved_institution,
            "authentication_method": resolved_auth,
            "module_id": module_id or _infer_module(event_type),
            "object_type": object_type,
            "object_id": object_id,
            "correlation_id": correlation_id,
            "causation_id": causation_id,
            "payload_hash": payload_hash,
            "provenance_refs": provenance_refs or [],
            "previous_event_hash": previous,
            "occurred_at": _iso(when),
        }
        event_hash = _hash(event_body)
        row = DecisionAuditEvent(
            id=_id(), stream_id=stream, decision_id=decision_id, sequence_no=sequence,
            event_type=event_type, actor_subject=actor_subject, actor_type=resolved_actor_type,
            institution_id=resolved_institution, authentication_method=resolved_auth,
            module_id=module_id or _infer_module(event_type), object_type=object_type,
            object_id=object_id, correlation_id=correlation_id, causation_id=causation_id,
            event_payload=body_payload, payload_hash=payload_hash, provenance_refs=provenance_refs or [],
            previous_event_hash=previous, event_hash=event_hash, occurred_at=when,
            metadata_json=metadata or {},
        )
        self.session.add(row)
        self.session.flush()
        return self._row_dict(row)

    def list(self, decision_id: str, *, event_type: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
        stmt = select(DecisionAuditEvent).where(DecisionAuditEvent.decision_id == decision_id).order_by(DecisionAuditEvent.sequence_no.asc())
        if event_type:
            stmt = stmt.where(DecisionAuditEvent.event_type == event_type)
        rows = list(self.session.scalars(stmt.limit(max(1, min(limit, 5000)))))
        return [self._row_dict(row) for row in rows]

    def get(self, decision_id: str, event_id: str) -> dict[str, Any]:
        row = self.session.get(DecisionAuditEvent, event_id)
        if row is None or row.decision_id != decision_id:
            raise LookupError("audit_event_not_found")
        return self._row_dict(row)

    def verify(self, decision_id: str) -> dict[str, Any]:
        events = self.list(decision_id, limit=5000)
        problems: list[dict[str, Any]] = []
        expected_previous = GENESIS_HASH
        expected_sequence = 1
        for event in events:
            if event["sequence_no"] != expected_sequence:
                problems.append({"event_id": event["event_id"], "problem": "sequence_gap", "expected": expected_sequence, "actual": event["sequence_no"]})
            if event["previous_event_hash"] != expected_previous:
                problems.append({"event_id": event["event_id"], "problem": "previous_hash_mismatch"})
            if _hash(event["payload"]) != event["payload_hash"]:
                problems.append({"event_id": event["event_id"], "problem": "payload_hash_mismatch"})
            body = {
                "schema": AUDIT_EVENT_SCHEMA,
                "stream_id": event["stream_id"],
                "decision_id": event["decision_id"],
                "sequence_no": event["sequence_no"],
                "event_type": event["event_type"],
                "actor_subject": event["actor"]["subject"],
                "actor_type": event["actor"]["type"],
                "institution_id": event["actor"]["institution_id"],
                "authentication_method": event["actor"]["authentication_method"],
                "module_id": event["module_id"],
                "object_type": event["object_type"],
                "object_id": event["object_id"],
                "correlation_id": event["correlation_id"],
                "causation_id": event["causation_id"],
                "payload_hash": event["payload_hash"],
                "provenance_refs": event["provenance_refs"],
                "previous_event_hash": event["previous_event_hash"],
                "occurred_at": event["occurred_at"],
            }
            if _hash(body) != event["event_hash"]:
                problems.append({"event_id": event["event_id"], "problem": "event_hash_mismatch"})
            expected_previous = event["event_hash"]
            expected_sequence = event["sequence_no"] + 1
        return {
            "schema": IMMUTABLE_AUDIT_LEDGER_SCHEMA,
            "decision_id": decision_id,
            "ok": not problems,
            "event_count": len(events),
            "problems": problems,
            "head_event_hash": events[-1]["event_hash"] if events else GENESIS_HASH,
        }

    def replay(self, decision_id: str) -> dict[str, Any]:
        events = self.list(decision_id, limit=5000)
        verification = self.verify(decision_id)
        return {
            "schema": DECISION_EVENT_STORE_SCHEMA,
            "decision_id": decision_id,
            "mode": "read-only-audit-replay",
            "reexecutes_domain_mutations": False,
            "event_count": len(events),
            "event_types": [event["event_type"] for event in events],
            "events": events,
            "verification": verification,
            "replay_digest_sha256": _hash([event["event_hash"] for event in events]),
        }

    def backfill_legacy_events(self, *, decision_id: str | None = None) -> dict[str, Any]:
        stmt = select(DecisionEvent).order_by(DecisionEvent.decision_id.asc(), DecisionEvent.sequence_no.asc(), DecisionEvent.occurred_at.asc())
        if decision_id:
            stmt = stmt.where(DecisionEvent.decision_id == decision_id)
        legacy = list(self.session.scalars(stmt))
        existing_legacy_ids = set()
        for audit_row in self.session.scalars(select(DecisionAuditEvent)):
            meta = audit_row.metadata_json or {}
            linked = meta.get("legacy_decision_event_id") or meta.get("compatibility_decision_event_id")
            if linked:
                existing_legacy_ids.add(str(linked))
        imported = 0
        skipped = 0
        for row in legacy:
            if row.id in existing_legacy_ids:
                skipped += 1
                continue
            self.append(
                decision_id=row.decision_id,
                event_type=row.event_type,
                payload=row.event_payload or {},
                actor_ref=row.actor_ref,
                actor_type="legacy-or-unknown",
                authentication_method="historical-backfill",
                occurred_at=row.occurred_at,
                metadata={"legacy_decision_event_id": row.id, "backfilled_in_release": "3.15.0"},
            )
            imported += 1
        return {"ok": True, "imported": imported, "skipped": skipped, "source_table": "decision_events"}


def _cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["backfill", "verify"])
    parser.add_argument("--decision-id")
    args = parser.parse_args()
    with session_scope() as session:
        repo = DecisionAuditLedgerRepository(session)
        if args.command == "backfill":
            print(json.dumps(repo.backfill_legacy_events(decision_id=args.decision_id), indent=2))
            return 0
        if not args.decision_id:
            raise SystemExit("--decision-id is required for verify")
        result = repo.verify(args.decision_id)
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(_cli())
