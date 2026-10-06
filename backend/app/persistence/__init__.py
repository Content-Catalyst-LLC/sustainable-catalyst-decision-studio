"""Decision Studio PostgreSQL persistence foundation (v3.3.0).

The v3.3 layer is deliberately non-authoritative. It establishes schema,
connectivity, migration, and repository contracts. Live decision ownership
moves to Python/PostgreSQL in v3.4.0.
"""
from .database import (
    EXPECTED_SCHEMA_REVISION,
    PERSISTENCE_AUTHORITY,
    PERSISTENCE_CONTRACT_SCHEMA,
    PERSISTENCE_SCHEMA,
    PERSISTENCE_TABLES,
    database_contract,
    database_schema_manifest,
    database_status,
)

__all__ = [
    "EXPECTED_SCHEMA_REVISION",
    "PERSISTENCE_AUTHORITY",
    "PERSISTENCE_CONTRACT_SCHEMA",
    "PERSISTENCE_SCHEMA",
    "PERSISTENCE_TABLES",
    "database_contract",
    "database_schema_manifest",
    "database_status",
]
