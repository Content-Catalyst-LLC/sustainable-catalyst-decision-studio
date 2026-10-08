# Decision Studio v3.15.0 backend package

Canonical schema revision: `0003_v3150_event_ledger`.

Persistence tables: 27. New table: `decision_audit_events`.

Canonical schemas:
- `scds-decision-event-store/1.0`
- `scds-immutable-audit-ledger/1.0`
- `scds-decision-audit-event/1.0`

The package contains the FastAPI backend, Alembic migrations, PostgreSQL persistence layer, v3.15 ledger runtime, global authentication integration, and deployment compose file. Production deployment requires a healthy v3.14 baseline at `0002_v3130_collaboration` / 26 tables, or a safe v3.15 rerun at `0003_v3150_event_ledger` / 27 tables.
