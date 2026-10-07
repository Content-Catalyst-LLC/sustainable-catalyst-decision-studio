# Decision Studio v3.9.0 — Unified Decision Module Registry

v3.9.0 establishes a canonical, kernel-governed registry for all four Decision Studio domains after the v3.5–v3.8 Python/PostgreSQL migration wave.

## Added

- `scds-unified-decision-module-registry/1.0`.
- Seven canonical registry endpoints for registry discovery, module lookup, capability indexing, provider indexing, readiness, and validation.
- Unified module metadata for domain schemas, storage/compute authority, capabilities, providers, security scopes, compatibility, and boundaries.
- Live readiness synthesis over all four module authority states plus PostgreSQL persistence readiness.
- Strict registry validation that rejects missing, duplicate, unknown, or authority/schema-mismatched modules.

## Preserved

- Canvas, Finance, Narrative Risk, and Global Impact Catalyst remain `python-domain-authoritative`.
- PostgreSQL remains the live persistence authority on Alembic revision `0001_v330_pg_foundation` with 20 tables.
- Workbench remains compute authority for Finance and Global Impact Catalyst.
- Existing `/decision-modules` and all four domain contract endpoints remain compatible.
- Final decision authority remains human-governed.

## Database

No schema migration is introduced by v3.9.0.
