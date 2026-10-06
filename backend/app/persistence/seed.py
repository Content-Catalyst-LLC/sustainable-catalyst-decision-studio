from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.decision_kernel import module_registry
from app.persistence.database import get_engine, database_url
from app.persistence.models import DecisionModule


def seed_module_registry() -> int:
    url = database_url()
    if not url:
        raise RuntimeError("SCDS_DATABASE_URL is required to seed Decision Studio persistence")
    engine = get_engine(url)
    assert engine is not None
    rows = []
    now = datetime.now(timezone.utc)
    for module in module_registry()["modules"]:
        rows.append({
            "module_id": module["module_id"],
            "display_name": module["display_name"],
            "contract_version": module["module_contract_schema"],
            "status": module.get("status", "foundation"),
            "contract_json": module,
            "created_at": now,
            "updated_at": now,
        })
    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            stmt = pg_insert(DecisionModule.__table__).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=[DecisionModule.module_id],
                set_={
                    "display_name": stmt.excluded.display_name,
                    "contract_version": stmt.excluded.contract_version,
                    "status": stmt.excluded.status,
                    "contract_json": stmt.excluded.contract_json,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            conn.execute(stmt)
        else:
            for row in rows:
                existing = conn.execute(
                    DecisionModule.__table__.select().where(DecisionModule.module_id == row["module_id"])
                ).first()
                if existing:
                    conn.execute(
                        DecisionModule.__table__.update().where(DecisionModule.module_id == row["module_id"]).values(**row)
                    )
                else:
                    conn.execute(DecisionModule.__table__.insert().values(**row))
    return len(rows)


if __name__ == "__main__":
    count = seed_module_registry()
    print(f"Seeded {count} Decision Studio module contracts")
