"""ExportJob model — persisted prepare step for export prepare/download pattern."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class ExportJobBase(SQLModel):
    """Base class for the ExportJob model."""

    export_path: str


class ExportJobCreate(ExportJobBase):
    """Model used when creating an export job."""


class ExportJobView(ExportJobBase):
    """Model used when retrieving an export job.

    Attributes:
        export_key: Unique identifier for the export job.
        export_path: Absolute path to the pre-generated export file or directory.
        created_at: Timestamp when the export job was created.
    """

    export_key: UUID
    created_at: datetime


class ExportJobTable(ExportJobBase, table=True):
    """One row per prepare call; consumed by the download endpoint.

    Attributes:
        export_key: Unique identifier for the export job (primary key).
        export_path: Absolute path to the pre-generated export file or directory.
        created_at: Timestamp when the export job was created.
    """

    __tablename__ = "export_job"

    export_key: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
