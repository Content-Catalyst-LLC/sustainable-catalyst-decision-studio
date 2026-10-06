# Decision Studio v3.4.0 — Python Decision Repository & Object Persistence

This release activates the Python/PostgreSQL repository prepared by v3.3.x. It does not add a new database schema revision. Instead, `0001_v330_pg_foundation` becomes the live storage substrate for Decision Kernel projects, decisions, unified Decision Objects, module bindings, snapshots, and audit events.

The release adds 13 repository endpoints, raises the certified API surface to 198 routes across 14 registry modules, preserves all v3.3.1 routes, and keeps all final decision authority human-governed. Legacy WordPress packet representations remain compatibility-preserved and can be imported idempotently without deleting their source representation.

Production deployment enables `SCDS_PERSISTENCE_WRITE_ENABLED=true` only after verifying PostgreSQL connectivity, the expected Alembic revision, the 20-table schema, and the four seeded module contracts.

Repository data endpoints are authenticated. The public authority descriptor contains no decision data; reads require `repository:read`, writes require `repository:write`, and the deployment creates a dedicated repository key in the private mode-600 persistence environment file when one does not already exist.
