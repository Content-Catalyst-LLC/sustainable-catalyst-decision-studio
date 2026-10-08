# Decision Studio v3.15.0 — Decision Event Store & Immutable Audit Ledger

Decision Studio v3.15.0 adds the canonical cross-module audit history for Decision Studio. It introduces a dedicated append-only PostgreSQL `decision_audit_events` table and Alembic revision `0003_v3150_event_ledger`, raising the authoritative persistence schema from 26 to 27 tables.

The ledger records deterministic per-stream sequence numbers, authenticated actor and institution identity, event/object/module identity, correlation and causation IDs, SHA-256 payload fingerprints, previous-event hashes, event hashes, provenance references, and timestamps. Normal application UPDATE and DELETE operations are rejected by database triggers. A controlled maintenance session setting exists only for backups, cleanup, and administrative recovery.

Existing repository/domain mutations automatically dual-write to the ledger through the canonical repository event seam. Historical `decision_events` can be backfilled idempotently. Audit replay is read-only and never re-executes domain mutations.

v3.15 preserves v3.14 global authentication, v3.13 Decision Room persistence, v3.12 shared evidence, v3.11 module artifact provenance, v3.10 composition, and all four authoritative module domains. Audit integrity does not establish truth, causality, recommendation, or approval; final decision authority remains human-governed.
