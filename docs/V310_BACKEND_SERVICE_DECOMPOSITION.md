# Decision Studio v3.1.0 — Backend Service Decomposition

## Purpose

v3.1.0 is the first decoupling-foundation release. It decomposes the FastAPI composition and route-registration layer without changing Decision Studio data authority, database schemas, WordPress persistence, or public HTTP route contracts.

## Architecture

- `backend/app/main.py` is now composition-only.
- `backend/app/api/router.py` aggregates domain route registries.
- `backend/app/api/routes/` contains **11** bounded router modules.
- `backend/app/services/decision_service.py` preserves the existing decision application behavior behind a service boundary.
- Existing specialized v2.x/v3.0 domain modules remain intact.
- Certified route inventory: **176** GET/POST API routes: 174 decomposed legacy routes plus the 2-route Energy Runtime consumer preserved as its existing specialist router.

## Router domains

- `system`: 11 routes
- `integrations`: 11 routes
- `decision_lifecycle`: 17 routes
- `collaboration`: 22 routes
- `institutional`: 18 routes
- `platform`: 8 routes
- `analysis`: 18 routes
- `objects`: 16 routes
- `evidence_analysis`: 27 routes
- `context_handoffs`: 16 routes
- `recommendations`: 10 routes
- existing `energy-runtime-consumer`: 2 routes (preserved specialist router)

## Explicit non-goals

- No PostgreSQL migration.
- No WordPress persistence migration.
- No authentication redesign.
- No Canvas/Finance/Narrative Risk/Global Impact module-contract migration yet.
- No public route removals or method changes.

Those begin in v3.2.0+ according to the Decision Studio modernization map.

## Certification gates

1. Existing backend test suite passes.
2. v3.1 architecture tests pass.
3. Certified route inventory is registered.
4. `/health` reports `3.1.0`.
5. `/release` reports `Backend Service Decomposition`.
6. Request-size and public rate-limit middleware remain active.
7. WordPress remains compatible with the existing API surface.
