# Decision Studio v3.6.0 — Finance Python Domain Migration

Decision Studio v3.6.0 moves Finance domain state into the authoritative Python/PostgreSQL repository while preserving Workbench as the compute authority.

## Added

- `scds-finance-domain/1.0` canonical Finance domain object.
- 11 `/finance` API routes with `finance:read` / `finance:write` authorization.
- Normalized Finance assumptions, financial scenarios/variables, uncertainty registrations, and Workbench computation receipts.
- Source-preserving, idempotent legacy Catalyst Finance import.
- Finance module registry state `python-domain-authoritative`.
- Shared-table domain ownership isolation between Canvas and Finance assumptions.

## Preserved

- Canvas Python domain authority from v3.5.0.
- Python/PostgreSQL repository authority from v3.4.0.
- PostgreSQL schema revision `0001_v330_pg_foundation` and 20-table inventory.
- WordPress legacy packet compatibility.
- Workbench as financial calculation/model execution authority.
- Human-governed final decision authority.

## Certification

- Full backend regression suite: PASS.
- Release integrity: PASS.
- 220 certified API routes across 16 route registry modules.
- 327 JSON artifacts validated.
- No database schema migration.
