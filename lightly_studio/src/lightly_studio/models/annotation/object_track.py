"""Object track model."""

from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlmodel import Field, SQLModel


class ObjectTrackTable(SQLModel, table=True):
    """Database table model for object tracks.

    Each row represents one tracked object. The track groups all
    per-frame annotations (stored in AnnotationBaseTable) that belong to the
    same physical object.
    """

    __tablename__ = "object_track"

    object_track_id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Numeric identifier for the object track.
    object_track_number: int

    # The dataset the object track belongs to.
    dataset_id: UUID = Field(foreign_key="dataset.dataset_id", index=True)

    # Vendor track id from the source annotations, unique per sequence not per dataset.
    source_track_id: int | None = None

    # Parent track for nested boxes, e.g. a truck cabin or bed.
    parent_object_track_id: UUID | None = Field(
        default=None, foreign_key="object_track.object_track_id", index=True
    )


class ObjectTrackView(BaseModel):
    """API response model for an object track."""

    model_config = ConfigDict(from_attributes=True)

    object_track_id: UUID
    object_track_number: int
    dataset_id: UUID
    source_track_id: int | None = None
    parent_object_track_id: UUID | None = None


class ObjectTrackCreate(SQLModel):
    """Input model for creating an object track."""

    object_track_number: int
    dataset_id: UUID
    source_track_id: int | None = None
    parent_object_track_id: UUID | None = None


class ObjectTrackWithCountView(BaseModel):
    """Response model for a list of object tracks with count."""

    model_config = ConfigDict(populate_by_name=True)

    tracks: list[ObjectTrackView]
    total_count: int
