"""Job model: the read model of a long-running job that the GUI polls."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column
from sqlmodel import Field, SQLModel

from lightly_studio.database import db_json


class JobStatus(str, Enum):
    """Lifecycle status of a job.

    `QUEUED` and `RUNNING` are active, the other statuses are terminal.
    """

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobBase(SQLModel):
    """Fields that the caller sets when it creates a job.

    Attributes:
        job_type: Kind of work the job does.
        resource_id: Resource that the job works on. There is no foreign key, because a job
            can work on resources of different tables.
        params: Parameters of the job.
    """

    job_type: str
    resource_id: UUID = Field(index=True)
    params: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(db_json.JSONB_TYPE, nullable=False),
    )


class JobTable(JobBase, table=True):
    """One row per job. The worker writes to the row and the GUI polls it.

    Jobs are PostgreSQL-only. DuckDB creates the table, but nothing writes to it. A resource
    has at most one active (`QUEUED` or `RUNNING`) job. A partial unique index from the
    migration enforces this.

    Attributes:
        job_id: Unique identifier of the job.
        engine_run_id: Identifier of the run in the job engine, `None` until the engine
            accepts the job.
        status: Current status of the job.
        progress: Progress in percent, from 0 to 100.
        attempt: The attempt that runs now or the last attempt that ran. 0 before the
            first run.
        message: Message for the user, e.g. the reason for a failure.
        created_at: Time when the job was created.
        started_at: Time when the job started to run.
        finished_at: Time when the job reached a terminal status.
    """

    __tablename__ = "job"

    job_id: UUID = Field(default_factory=uuid4, primary_key=True)
    engine_run_id: str | None = None
    status: JobStatus = JobStatus.QUEUED
    progress: int = Field(default=0, ge=0, le=100)
    attempt: int = 0
    message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    finished_at: datetime | None = None


class JobCreate(JobBase):
    """Input model to create a job."""


class JobView(BaseModel):
    """API view of a job."""

    model_config = ConfigDict(from_attributes=True)

    job_id: UUID
    job_type: str
    resource_id: UUID
    engine_run_id: str | None
    status: JobStatus
    progress: int
    attempt: int
    message: str | None
    params: dict[str, Any]
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
