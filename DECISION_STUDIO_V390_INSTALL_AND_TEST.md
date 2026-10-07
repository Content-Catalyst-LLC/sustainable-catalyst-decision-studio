# Install and Test Decision Studio v3.9.0

Use `APPLY_AND_PUSH_DECISION_STUDIO_V390.sh` against a clean v3.8.0 checkout. The script creates a temporary Python 3.12 environment outside the repository, runs the complete backend regression suite and static release certification, pushes/tag v3.9.0, and builds distributables.

Deploy production with `deploy_decision_studio_v3_9_0_from_macos.sh`. The guarded VPS upgrader requires the v3.8 four-domain authoritative baseline, 20 persistence tables, and Alembic revision `0001_v330_pg_foundation` before deployment.
