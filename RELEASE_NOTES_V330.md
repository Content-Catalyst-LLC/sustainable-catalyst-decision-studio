# Decision Studio v3.3.0 — PostgreSQL Persistence Foundation

Decision Studio now has a production PostgreSQL persistence foundation behind the shared v3.2 Decision Kernel.

The release adds SQLAlchemy 2 domain persistence models, Psycopg 3 connectivity, Alembic migrations, a 20-table initial schema, module-registry seeding, repository interfaces, persistence health/contract endpoints, and Contabo PostgreSQL provisioning and backup/migration checks.

PostgreSQL is deliberately **non-authoritative in v3.3.0**. Existing Decision Studio behavior and WordPress authority remain intact while the new database layer is exercised in production. v3.4.0 will migrate live Decision Studio object ownership into the Python repository layer.
