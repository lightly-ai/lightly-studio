"""Annotation layer table model."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
    from lightly_studio.models.sample import SampleTable
else:
    AnnotationBaseTable = object
    SampleTable = object


class AnnotationLayerTable(SQLModel, table=True):
    """Stores stack position for each annotation layer."""

    __tablename__ = "annotation_layer"

    layer_id: UUID = Field(default_factory=uuid4, primary_key=True)
    annotation_id: UUID = Field(
        foreign_key="annotation_base.sample_id",
        unique=True,
        index=True,
    )
    sample_id: UUID = Field(foreign_key="sample.sample_id", index=True)
    position: int = Field(index=True)

    annotation: Mapped["AnnotationBaseTable"] = Relationship(back_populates="layer")
    sample: Mapped["SampleTable"] = Relationship()
