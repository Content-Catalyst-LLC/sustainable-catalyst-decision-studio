# Decision Studio v3.3.1 — Install and Test

Use `APPLY_AND_PUSH_DECISION_STUDIO_V331.sh` from the extracted v3.3.1 repository bundle. It overlays the repair onto the existing v3.3.0 Git checkout, validates with a temporary Python 3.12 environment, runs the full suite plus migration regression checks, commits/pushes/tags v3.3.1, and builds distributables into `~/Downloads`.

The Contabo upgrader reuses the existing PostgreSQL credential file and Docker volume created by the failed v3.3.0 attempt, runs the corrected Alembic migration idempotently, seeds the four module contracts, and verifies the database remains non-authoritative.
