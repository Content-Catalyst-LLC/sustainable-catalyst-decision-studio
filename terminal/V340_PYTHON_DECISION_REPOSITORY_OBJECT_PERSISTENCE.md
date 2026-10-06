# Decision Studio v3.4.0 — Python Decision Repository & Object Persistence

v3.4.0 performs the storage-authority cutover prepared by v3.3.x. The existing PostgreSQL 20-table schema remains unchanged at Alembic revision `0001_v330_pg_foundation`; the change in this release is application authority, not schema shape.

## Authority model

- Python/PostgreSQL is authoritative for Decision Kernel project, decision, unified Decision Object, module-binding, snapshot, and repository event persistence.
- WordPress Decision Object persistence is no longer canonical.
- Legacy WordPress packet and collaboration representations remain compatibility-preserved and can be projected/imported without source deletion.
- Final decisions, approvals, recommendation dispositions, and external execution remain human-governed.
- Finance computation remains delegated to Workbench.

## Repository API

The `scds-python-decision-repository/1.0` surface adds project/decision CRUD, authoritative unified object persistence, module bindings, snapshots, authority inspection, and idempotent legacy object import.

## Database boundary

No new Alembic migration is introduced. Production must already be on `0001_v330_pg_foundation` with all 20 v3.3 tables present. Deployment fails closed if the revision or table inventory is not current.
