# Decision Studio v3.5.0 — Canvas Python Domain Migration

This release makes Canvas the first Decision Studio module to complete its Python domain migration after the v3.4 repository-authority cutover.

- Adds `scds-canvas-domain/1.0`.
- Adds 11 native Canvas API operations.
- Normalizes alternatives, criteria, and assumptions into PostgreSQL.
- Keeps problem framing, objectives/constraints, stakeholders, success measures, and provenance in the canonical Canvas domain object.
- Adds source-preserving legacy Catalyst Canvas import.
- Preserves all v3.4 repository APIs and all earlier routes.
- Adds no Alembic migration; revision remains `0001_v330_pg_foundation` with 20 tables.
- Keeps Finance compute authority in Workbench.
- Keeps final decision authority human-governed.

Next: v3.6.0 — Finance Python Domain Migration.
