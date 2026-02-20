"""Object track model."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from lightly_studio.models.annotation.annotation_base import (
        AnnotationBaseTable,
        AnnotationView,
    )
else:
    AnnotationBaseTable = object
    AnnotationView = object


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

    annotations: Mapped[list["AnnotationBaseTable"]] = Relationship(
        back_populates="object_track",
        sa_relationship_kwargs={"lazy": "select"},
    )


class ObjectTrackView(BaseModel):
    """API response model for an object track."""

    model_config = ConfigDict(from_attributes=True)

    object_track_id: UUID
    object_track_number: int
    annotations: list["AnnotationView"] = []


class ObjectTrackCreate(SQLModel):
    """Input model for creating an object track."""

    object_track_number: int


class ObjectTrackWithCountView(BaseModel):
    """Response model for a list of object tracks with count."""

    model_config = ConfigDict(populate_by_name=True)

    tracks: list[ObjectTrackView]
    total_count: int
