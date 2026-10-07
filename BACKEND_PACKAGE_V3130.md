# Decision Studio Backend v3.13.0

Release: **Collaboration & Decision Room Python Persistence**

The backend package contains FastAPI runtime v3.13.0, the Python/PostgreSQL repository, four authoritative Decision Studio module domains, Unified Module Registry, Cross-Module Composition, Module Artifact & Provenance, Shared Evidence interoperability, and authoritative persisted Decision Rooms.

Production expectations:

- PostgreSQL authority: `python-postgresql`
- Previous Alembic revision: `0001_v330_pg_foundation`
- Target Alembic revision: `0002_v3130_collaboration`
- Previous persistence tables: 20
- Target persistence tables: 26
- New collaboration tables: 6
- Room snapshots: existing `snapshots` table
- API routes: 293
- Route registries: 23
- WordPress room persistence: compatibility-only
- Canonical room persistence: Python/PostgreSQL
- Final decision authority: human-governed
