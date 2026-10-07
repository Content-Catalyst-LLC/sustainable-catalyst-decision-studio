# Decision Studio v3.5.0 — Canvas Python Domain Migration

v3.5.0 moves Canvas from a first-class module contract and legacy Catalyst Canvas adapter into an authoritative Python/PostgreSQL domain over the shared Decision Kernel and v3.4 repository.

## Authority

Canvas is authoritative for problem framing, objectives and constraints, stakeholder context, alternatives, criteria, assumptions, success measures, framing notes, and framing provenance. Shared decision identity and lifecycle remain Decision Kernel responsibilities. Final decisions remain human-governed.

## Persistence

No schema migration is introduced. Canvas reuses the certified v3.3/v3.4 PostgreSQL schema and Alembic revision `0001_v330_pg_foundation`.

Canvas stores a canonical `scds-canvas-domain/1.0` object in `decision_objects` and normalizes alternatives, criteria, and assumptions into their shared relational tables. Module bindings and audit events use the existing `decision_module_bindings` and `decision_events` tables.

## API

v3.5 adds 11 routes under `/canvas`. Contract/template endpoints are public. Decision data requires `canvas:read` or `canvas:write`; the repository key and super-key are also authorized.

## Legacy migration

`POST /canvas/import/legacy` promotes a legacy Catalyst Canvas artifact into the Python repository while preserving the original artifact in provenance. Re-import targets the same decision identity when a stable decision ID is supplied.

## Boundaries

Canvas does not own shared decision identity, does not execute Workbench calculations, does not auto-select a winner, does not auto-recommend, and does not approve a decision.
