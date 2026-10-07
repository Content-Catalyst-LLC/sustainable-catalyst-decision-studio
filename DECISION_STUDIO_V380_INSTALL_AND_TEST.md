# Install and test Decision Studio v3.8.0

Use Python 3.12 for local validation. The provided `APPLY_AND_PUSH_DECISION_STUDIO_V380.sh` creates a temporary venv outside the repository, overlays the certified source onto an existing clean v3.7.0 checkout, runs the complete backend regression suite and release-integrity checks, pushes/tag v3.8.0, and builds distributables.

Production deployment is performed with `deploy_decision_studio_v3_8_0_from_macos.sh`, which calls the guarded Contabo upgrader. The upgrader requires the existing authoritative v3.7 repository, PostgreSQL revision `0001_v330_pg_foundation`, and 20-table schema before activating Global Impact authority.
