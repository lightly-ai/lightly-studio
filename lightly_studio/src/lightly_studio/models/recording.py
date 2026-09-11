"""Recording model.

A recording is the physical file (e.g. an ``.mcap``) that a dataset was indexed from. It stores
where the bytes are (``uri``) and what format they are.
"""

from enum import Enum
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class RecordingFormat(str, Enum):
    """Supported recording file formats."""

    MCAP = "mcap"


class RecordingBase(SQLModel):
    """Shared fields for the Recording model."""

    format: RecordingFormat
    uri: str


class RecordingCreate(RecordingBase):
    """Input model for creating a recording."""

    dataset_id: UUID


class RecordingTable(RecordingBase, table=True):
    """Database table model for recordings."""

    __tablename__ = "recording"

    recording_id: UUID = Field(default_factory=uuid4, primary_key=True)

    # The dataset the recording belongs to.
    dataset_id: UUID = Field(foreign_key="dataset.dataset_id", index=True)
