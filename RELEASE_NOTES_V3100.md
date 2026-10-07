# Decision Studio v3.10.0 — Cross-Module Decision Composition

v3.10.0 introduces a governed composition layer over the four authoritative Decision Studio domains: Canvas, Finance, Narrative Risk, and Global Impact Catalyst.

## New canonical contract

- `scds-cross-module-decision-composition/1.0`
- Stored in the existing `decision_objects` table as `cross-module-decision-composition`
- No PostgreSQL/Alembic schema migration
- Minimum two selected modules
- Explicit cross-module links only; no inferred relationship, truth, causality, winner, recommendation, or approval
- Module-owned objects retain their source module identity in the shared Kernel projection
- Module fingerprints support stale-composition diagnostics and explicit refresh

## New API

- `GET /decision-composition/contract`
- `GET /decision-composition/template`
- `POST /decision-composition/validate`
- `GET /decision-composition/decisions/{decision_id}`
- `PUT /decision-composition/decisions/{decision_id}`
- `POST /decision-composition/decisions/{decision_id}/refresh`
- `GET /decision-composition/decisions/{decision_id}/diagnostics`

## Authority boundaries

- Storage: Python/PostgreSQL
- Finance compute: Workbench
- Global Impact compute: Workbench
- Canvas, Finance, Narrative Risk and Global Impact remain independently authoritative for their own domain state
- Shared decision identity remains owned by the Decision Kernel
- Final decision authority remains human-governed

## Release certification target

- 256 certified API routes
- 20 route registries plus Energy Runtime router (21 included routers)
- 20 PostgreSQL tables
- Alembic revision remains `0001_v330_pg_foundation`
- v3.9 Unified Decision Module Registry preserved
- WordPress remains compatibility/client surface; no new authority cutover
