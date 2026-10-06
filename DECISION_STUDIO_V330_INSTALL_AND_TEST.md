# Decision Studio v3.3.0 — Install and Test

Use `APPLY_AND_PUSH_DECISION_STUDIO_V330.sh` from the extracted v3.3 repository bundle. The script uses a temporary Python 3.12 virtual environment outside the Git checkout, installs the pinned backend requirements, runs the complete pytest suite including Alembic upgrade/downgrade certification, runs static release integrity checks, commits/pushes/tags v3.3.0, and builds distributables into `~/Downloads`.

Deploy only after the local apply script reports PASS. The Contabo upgrader backs up the v3.2 runtime, provisions PostgreSQL 16 with persistent storage, applies Alembic revision `0001_v330_postgresql_persistence_foundation`, seeds the four module contracts, and verifies the database remains non-authoritative.
