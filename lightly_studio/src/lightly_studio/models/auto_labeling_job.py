"""This module contains the AutoLabelingJob model."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlmodel import Field, JSON, SQLModel, String


class AutoLabelingJobStatus(str, Enum):
    """Status of an auto-labeling job."""

    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class AutoLabelingJobTable(SQLModel, table=True):
    """Database table for auto-labeling jobs."""

    __tablename__ = "auto_labeling_job"

    job_id: UUID = Field(default_factory=uuid4, primary_key=True)
    collection_id: UUID = Field(foreign_key="collection.collection_id")
    provider_id: str  # e.g., "chatgpt_captioning"
    status: AutoLabelingJobStatus = Field(sa_type=String)
    parameters: dict[str, Any] = Field(default={}, sa_type=JSON)

    processed_count: int = 0
    error_count: int = 0
    error_message: str | None = None
    result_tag_id: UUID | None = Field(default=None, foreign_key="tag.tag_id")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None


class AutoLabelingJobCreate(SQLModel):
    """Model for creating an auto-labeling job."""

    collection_id: UUID
    provider_id: str
    parameters: dict[str, Any]
    status: AutoLabelingJobStatus = AutoLabelingJobStatus.pending


class AutoLabelingJobView(SQLModel):
    """Model for viewing an auto-labeling job."""

    job_id: UUID
    collection_id: UUID
    provider_id: str
    status: AutoLabelingJobStatus
    processed_count: int
    error_count: int
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
