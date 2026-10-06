from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

REPOSITORY_SCHEMA = "scds-python-decision-repository/1.0"
REPOSITORY_AUTHORITY = "python-postgresql"


class ProjectCreate(BaseModel):
    project_id: str | None = Field(default=None, max_length=64)
    title: str = Field(min_length=1, max_length=300)
    status: str = Field(default="active", max_length=64)
    owner_ref: str | None = Field(default=None, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionCreate(BaseModel):
    decision_id: str | None = Field(default=None, max_length=64)
    project_id: str | None = Field(default=None, max_length=64)
    decision_question: str = Field(min_length=1)
    lifecycle_state: str = Field(default="framing", max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionPatch(BaseModel):
    project_id: str | None = Field(default=None, max_length=64)
    decision_question: str | None = None
    lifecycle_state: str | None = Field(default=None, max_length=64)
    metadata: dict[str, Any] | None = None


class DecisionObjectUpsert(BaseModel):
    object_id: str | None = Field(default=None, max_length=64)
    schema_id: str = Field(default="scds-decision-object/1.0", max_length=255)
    payload: dict[str, Any] = Field(default_factory=dict)
    provenance_ref: str | None = Field(default=None, max_length=255)


class ModuleBindingUpsert(BaseModel):
    enabled: bool = True
    configuration: dict[str, Any] = Field(default_factory=dict)


class SnapshotCreate(BaseModel):
    snapshot_id: str | None = Field(default=None, max_length=64)
    snapshot_type: str = Field(default="decision", max_length=96)
    payload: dict[str, Any] = Field(default_factory=dict)
    provenance_ref: str | None = Field(default=None, max_length=255)


class DecisionObjectImport(BaseModel):
    decision_object: dict[str, Any] = Field(default_factory=dict)
    project_id: str | None = Field(default=None, max_length=64)
    project_title: str | None = Field(default=None, max_length=300)
    owner_ref: str | None = Field(default=None, max_length=255)
    provenance_ref: str | None = Field(default=None, max_length=255)
