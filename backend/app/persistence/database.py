from __future__ import annotations

import os
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Iterator
from urllib.parse import urlsplit

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

PERSISTENCE_SCHEMA = "scds-postgresql-persistence/1.0"
PERSISTENCE_CONTRACT_SCHEMA = "scds-persistence-authority-contract/1.0"
EXPECTED_SCHEMA_REVISION = "0001_v330_postgresql_persistence_foundation"
PERSISTENCE_AUTHORITY = "non-authoritative-foundation"
PERSISTENCE_TABLES = tuple(sorted(Base.metadata.tables.keys()))


def database_url() -> str:
    return os.getenv("SCDS_DATABASE_URL", "").strip()


def persistence_required() -> bool:
    return os.getenv("SCDS_PERSISTENCE_REQUIRED", "false").strip().lower() in {"1", "true", "yes", "on"}


def persistence_write_enabled() -> bool:
    # v3.3 intentionally defaults false. v3.4 owns the authority cutover.
    return os.getenv("SCDS_PERSISTENCE_WRITE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def _safe_location(url: str) -> dict[str, str | None]:
    if not url:
        return {"dialect": None, "host": None, "database": None}
    normalized = url.replace("postgresql+psycopg://", "postgresql://", 1)
    parts = urlsplit(normalized)
    return {
        "dialect": parts.scheme or None,
        "host": parts.hostname,
        "database": (parts.path or "").lstrip("/") or None,
    }


@lru_cache(maxsize=4)
def engine_for_url(url: str) -> Engine:
    kwargs: dict[str, Any] = {"pool_pre_ping": True, "future": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


def get_engine(url: str | None = None) -> Engine | None:
    target = (url if url is not None else database_url()).strip()
    if not target:
        return None
    return engine_for_url(target)


@contextmanager
def session_scope(url: str | None = None) -> Iterator[Session]:
    engine = get_engine(url)
    if engine is None:
        raise RuntimeError("Decision Studio persistence is not configured")
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def current_revision(engine: Engine) -> str | None:
    try:
        with engine.connect() as conn:
            return conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar_one_or_none()
    except Exception:
        return None


def database_status(url: str | None = None) -> dict[str, Any]:
    target = (url if url is not None else database_url()).strip()
    location = _safe_location(target)
    required = persistence_required() if url is None else False
    base: dict[str, Any] = {
        "schema": PERSISTENCE_SCHEMA,
        "contract_schema": PERSISTENCE_CONTRACT_SCHEMA,
        "authority": PERSISTENCE_AUTHORITY,
        "configured": bool(target),
        "required": required,
        "write_enabled": persistence_write_enabled() if url is None else False,
        "connected": False,
        "schema_revision": None,
        "expected_schema_revision": EXPECTED_SCHEMA_REVISION,
        "schema_current": False,
        "table_count": len(PERSISTENCE_TABLES),
        "dialect": location["dialect"],
        "host": location["host"],
        "database": location["database"],
        "error": None,
    }
    if not target:
        return base
    try:
        engine = get_engine(target)
        assert engine is not None
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        revision = current_revision(engine)
        existing = set(inspect(engine).get_table_names())
        base.update(
            connected=True,
            schema_revision=revision,
            schema_current=(revision == EXPECTED_SCHEMA_REVISION and set(PERSISTENCE_TABLES).issubset(existing)),
        )
    except Exception as exc:  # health/status must never leak credentials
        message = str(exc).splitlines()[0]
        if target:
            message = message.replace(target, "<database-url-redacted>")
        # Redact any URL-like authority credentials that a driver may echo.
        import re
        message = re.sub(r"(postgres(?:ql)?(?:\+\w+)?://)[^@\s]+@", r"\1<credentials-redacted>@", message)
        base["error"] = f"{type(exc).__name__}: {message[:240]}"
    return base


def database_contract() -> dict[str, Any]:
    return {
        "schema": PERSISTENCE_CONTRACT_SCHEMA,
        "persistence_schema": PERSISTENCE_SCHEMA,
        "authority": PERSISTENCE_AUTHORITY,
        "principles": {
            "postgresql_is_live_authority": False,
            "wordpress_authority_changed": False,
            "python_repository_authority_changed": False,
            "schema_migration_present": True,
            "writes_enabled_by_default": False,
            "v3_4_authority_cutover_required": True,
            "decision_kernel_contract_preserved": True,
            "final_decision_authority": "human-governed",
        },
        "expected_schema_revision": EXPECTED_SCHEMA_REVISION,
        "tables": list(PERSISTENCE_TABLES),
    }


def database_schema_manifest() -> dict[str, Any]:
    return {
        "schema": PERSISTENCE_SCHEMA,
        "revision": EXPECTED_SCHEMA_REVISION,
        "table_count": len(PERSISTENCE_TABLES),
        "tables": list(PERSISTENCE_TABLES),
        "module_registry_seed": ["canvas", "finance", "narrative-risk", "global-impact"],
        "migration_tool": "alembic",
        "orm": "sqlalchemy-2",
        "driver": "psycopg-3",
        "authority": PERSISTENCE_AUTHORITY,
    }
