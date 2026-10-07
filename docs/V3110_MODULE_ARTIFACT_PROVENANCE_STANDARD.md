# Decision Studio v3.11.0 — Module Artifact & Provenance Standard

Decision Studio v3.11.0 adds one canonical artifact and provenance envelope for Canvas, Finance, Narrative Risk, Global Impact, and cross-module decision work.

## Core contracts

- `scds-module-artifact/1.0`
- `scds-module-provenance/1.0`

## Guarantees

- Stable logical artifact identity across immutable revisions.
- SHA-256 integrity fingerprint for every stored revision.
- Explicit module ownership.
- Explicit parent-artifact lineage.
- Preserved source, evidence, and external-computation references.
- Artifact/provenance persistence uses existing `artifacts` and `decision_events` tables.
- No database schema migration; Alembic remains `0001_v330_pg_foundation` with 20 tables.

## Authority boundaries

- Decision Studio Kernel owns module-artifact provenance records.
- Platform Core remains authority for evidence identity and source provenance.
- Workbench remains compute authority for Finance and Global Impact calculations.
- Provenance does not prove truth or causality.
- An artifact never implies recommendation, approval, or final decision.
- Final decision authority remains human-governed.

## API

Eight additive `/module-artifacts` routes provide contract/template validation, artifact creation/list/get, immutable revision creation, and lineage inspection.
