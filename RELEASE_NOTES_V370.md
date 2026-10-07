# Decision Studio v3.7.0 — Narrative Risk Python Domain Migration

Decision Studio v3.7.0 moves Narrative Risk domain state into the authoritative Python/PostgreSQL repository while preserving evidence provenance and human judgment boundaries.

## Delivered

- Authoritative `scds-narrative-risk-domain/1.0` domain.
- 11 scoped Narrative Risk API routes.
- Claims and risk hypotheses normalized into `claims`.
- Evidence relationships normalized into `evidence_links`.
- Signals normalized into `artifacts` as `narrative-risk-signal`.
- Actors, exposures, competing narratives, watch conditions, mitigations, notes, and provenance preserved in the canonical Narrative Risk decision object.
- Source-preserving legacy Narrative Risk import.
- Explicit domain ownership metadata so replacement operations do not delete Finance, Canvas, or future module records.
- No automatic truth verification, causality inference, recommendation, escalation, or action.
- Canvas and Finance remain Python-domain-authoritative; Workbench remains Finance compute authority.
- No database schema migration; Alembic remains `0001_v330_pg_foundation` with 20 persistence tables.

Next: v3.8.0 — Global Impact Catalyst Python Domain Migration.
