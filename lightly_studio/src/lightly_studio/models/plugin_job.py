"""This module contains the PluginJob model."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlmodel import Field, JSON, SQLModel, String


class PluginJobStatus(str, Enum):
    """Status of a plugin job."""

    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class PluginJobTable(SQLModel, table=True):
    """Database table for plugin jobs."""

    # Keep original table name to avoid DB migration
    __tablename__ = "auto_labeling_job"

    job_id: UUID = Field(default_factory=uuid4, primary_key=True)
    collection_id: UUID = Field(foreign_key="collection.collection_id")
    provider_id: str  # operator ID, e.g., "chatgpt_captioning"
    status: PluginJobStatus = Field(sa_type=String)
    parameters: dict[str, Any] = Field(default={}, sa_type=JSON)

    processed_count: int = 0
    error_count: int = 0
    error_message: str | None = None
    result_tag_id: UUID | None = Field(default=None, foreign_key="tag.tag_id")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None


class PluginJobCreate(SQLModel):
    """Model for creating a plugin job."""

    collection_id: UUID
    provider_id: str
    parameters: dict[str, Any]
    status: PluginJobStatus = PluginJobStatus.pending


class PluginJobView(SQLModel):
    """Model for viewing a plugin job."""

    job_id: UUID
    collection_id: UUID
    provider_id: str
    status: PluginJobStatus
    processed_count: int
    error_count: int
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
