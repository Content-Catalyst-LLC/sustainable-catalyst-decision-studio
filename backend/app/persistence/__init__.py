"""Decision Studio authoritative Python/PostgreSQL persistence layer (v3.4.0)."""
from .contracts import (
    REPOSITORY_AUTHORITY,
    REPOSITORY_SCHEMA,
    DecisionCreate,
    DecisionObjectImport,
    DecisionObjectUpsert,
    DecisionPatch,
    ModuleBindingUpsert,
    ProjectCreate,
    SnapshotCreate,
)
from .database import (
    EXPECTED_SCHEMA_REVISION,
    PERSISTENCE_AUTHORITY,
    PERSISTENCE_CONTRACT_SCHEMA,
    PERSISTENCE_SCHEMA,
    PERSISTENCE_TABLES,
    database_contract,
    database_schema_manifest,
    database_status,
    persistence_write_enabled,
    session_scope,
)
from .repository import PersistenceRepository

__all__ = [
    "EXPECTED_SCHEMA_REVISION",
    "PERSISTENCE_AUTHORITY",
    "PERSISTENCE_CONTRACT_SCHEMA",
    "PERSISTENCE_SCHEMA",
    "PERSISTENCE_TABLES",
    "REPOSITORY_AUTHORITY",
    "REPOSITORY_SCHEMA",
    "ProjectCreate",
    "DecisionCreate",
    "DecisionPatch",
    "DecisionObjectUpsert",
    "ModuleBindingUpsert",
    "SnapshotCreate",
    "DecisionObjectImport",
    "PersistenceRepository",
    "database_contract",
    "database_schema_manifest",
    "database_status",
    "persistence_write_enabled",
    "session_scope",
]
