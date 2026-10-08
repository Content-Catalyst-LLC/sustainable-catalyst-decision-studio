# v3.15.0 — Decision Event Store & Immutable Audit Ledger

v3.15.0 establishes a canonical append-only audit ledger across Decision Studio. Repository and domain event writes are captured in `decision_audit_events`, ordered per decision stream, SHA-256 hash chained, bound to authenticated actors/institutions when available, and verifiable without re-executing business logic.

The PostgreSQL schema advances from `0002_v3130_collaboration` / 26 tables to `0003_v3150_event_ledger` / 27 tables. Database triggers reject normal UPDATE and DELETE operations. Historical `decision_events` may be backfilled idempotently.

Audit integrity is evidence of ledger integrity only. It does not establish truth, causality, recommendation correctness, authorization to act, or approval. Final decision authority remains human-governed.
