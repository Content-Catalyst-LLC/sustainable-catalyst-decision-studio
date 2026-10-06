# Decision Studio v3.3.1 — PostgreSQL Migration Revision Repair

This patch repairs the production Alembic migration failure discovered during v3.3.0 deployment. Alembic creates `alembic_version.version_num` as `VARCHAR(32)` by default; the original v3.3.0 revision identifier exceeded that limit.

The replacement revision is `0001_v330_pg_foundation` (23 characters). The 20-table schema, four module seeds, PostgreSQL 16 runtime, non-authoritative persistence boundary, and all 185 API routes are unchanged. PostgreSQL is still not the live Decision Studio authority; that cutover remains v3.4.0.
