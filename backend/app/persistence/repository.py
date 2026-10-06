from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import PERSISTENCE_AUTHORITY
from .models import Decision, DecisionModule, DecisionProject


class PersistenceRepository:
    """v3.3 repository foundation.

    These methods are intentionally not wired into live Decision Studio write
    endpoints in v3.3. They provide the repository seam for the v3.4 authority
    migration.
    """

    authority = PERSISTENCE_AUTHORITY

    def __init__(self, session: Session):
        self.session = session

    def get_project(self, project_id: str) -> DecisionProject | None:
        return self.session.get(DecisionProject, project_id)

    def get_decision(self, decision_id: str) -> Decision | None:
        return self.session.get(Decision, decision_id)

    def list_decisions(self, project_id: str | None = None) -> list[Decision]:
        stmt = select(Decision).order_by(Decision.created_at.desc())
        if project_id:
            stmt = stmt.where(Decision.project_id == project_id)
        return list(self.session.scalars(stmt))

    def list_modules(self) -> list[DecisionModule]:
        return list(self.session.scalars(select(DecisionModule).order_by(DecisionModule.module_id)))

    def authority_descriptor(self) -> dict[str, Any]:
        return {
            "authority": self.authority,
            "live_write_authority": False,
            "cutover_release": "3.4.0",
        }
