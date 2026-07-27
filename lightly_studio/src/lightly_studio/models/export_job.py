"""ExportJob model — persisted prepare step for export prepare/download pattern."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class ExportType(str, Enum):
    """Discriminator for which export endpoint a key belongs to."""

    ANNOTATIONS = "annotations"
    CAPTIONS = "captions"
    YOUTUBE_VIS = "youtube_vis"
    FILENAME = "filename"


class ExportJobTable(SQLModel, table=True):
    """One row per prepare call; consumed by the matching download endpoint."""

    __tablename__ = "export_job"

    export_key: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    export_type: ExportType
    collection_id: UUID
    filter_json: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
