# Decision Studio v3.3.0 — PostgreSQL Persistence Foundation

v3.3.0 introduces a production PostgreSQL persistence layer without moving live Decision Studio ownership yet.

## Boundary

- Database migration: **yes**.
- PostgreSQL service in production: **yes**.
- Alembic schema revision: `0001_v330_postgresql_persistence_foundation`.
- PostgreSQL live decision authority: **no**.
- Python repository live authority: **no**.
- WordPress authority change: **no**.
- Default persistence writes from product APIs: **disabled**.
- Authority cutover target: **v3.4.0**.

This distinction allows the schema, migrations, backups, connectivity, and observability to be certified before live decision objects depend on the new store.

## Persistence tables

The initial schema contains 20 tables: `decision_projects`, `decisions`, `decision_objects`, `decision_modules`, `decision_module_bindings`, `alternatives`, `criteria`, `criterion_values`, `assumptions`, `claims`, `evidence_links`, `scenarios`, `scenario_variables`, `uncertainty_models`, `recommendations`, `reviews`, `challenges`, `decision_events`, `artifacts`, and `snapshots`.

## Runtime endpoints

- `GET /persistence/status`
- `GET /persistence/schema`
- `GET /persistence/contract`

Production health can require an available database at the expected schema revision while still reporting `authority=non-authoritative-foundation`.

## Production deployment

The v3.3 Contabo deploy workflow creates a private PostgreSQL credential file when needed, starts PostgreSQL 16, runs `alembic upgrade head`, seeds the four v3.2 module contracts into `decision_modules`, starts the v3.3 backend, and verifies both internal and public persistence status.
