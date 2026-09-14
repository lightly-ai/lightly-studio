"""Recording model for dataset-owned media files."""

from enum import Enum
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class RecordingFormat(str, Enum):
    """Supported recording formats."""

    MCAP = "mcap"


class RecordingBase(SQLModel):
    """Shared recording fields."""

    format: RecordingFormat
    uri: str


class RecordingTable(RecordingBase, table=True):
    """A dataset-scoped recording stored locally or in object storage."""

    __tablename__ = "recording"

    recording_id: UUID = Field(default_factory=uuid4, primary_key=True)
    dataset_id: UUID = Field(foreign_key="dataset.dataset_id", index=True)


class RecordingView(RecordingBase):
    """API representation of a recording and its browser media endpoint."""

    recording_id: UUID
    dataset_id: UUID
    media_url: str
    size_bytes: int
    etag: str
