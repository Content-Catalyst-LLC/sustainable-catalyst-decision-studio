# Decision Studio Backend v3.14.0

The backend package contains the FastAPI service, Alembic history through `0002_v3130_collaboration`, and the v3.14 global authentication/authorization relying-party runtime.

Production requirements: Python 3.12 container runtime, PostgreSQL at revision `0002_v3130_collaboration`, the existing persistence environment file, and a private `SCDS_GLOBAL_AUTH_JWT_SECRET`. The guarded upgrader creates that secret only if absent and never rotates an existing value automatically.

Certified application API count: **300** routes across **24 route registries / 25 included routers**. Seven routes are under `/auth/*`.
