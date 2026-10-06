# Decision Studio v3.3.0 Backend Package

The backend package contains the FastAPI application, SQLAlchemy persistence models, Alembic configuration and initial migration, requirements, Dockerfile, and the v3.3 Compose template used by the guarded Contabo upgrader.

Production PostgreSQL credentials are generated on the VPS at `/opt/sustainable-catalyst/decision-studio/.env.persistence-v330` with mode `600`; they are not included in release archives.
