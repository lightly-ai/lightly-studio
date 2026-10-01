"""3D cuboid annotation models.

A cuboid is a 9-DoF box (centre, size, quaternion) expressed in a named
coordinate frame. It is parented to a tick group, not to a single sensor.
"""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from lightly_studio.models.annotation.annotation_base import (
        AnnotationBaseTable,
    )
else:
    AnnotationBaseTable = object


class Cuboid3DCreate(SQLModel):
    """Pose and size of a cuboid, used when creating an annotation."""

    frame_id: str
    px: float
    py: float
    pz: float
    qx: float
    qy: float
    qz: float
    qw: float
    sx: float
    sy: float
    sz: float
    interpolated: bool = False


class Cuboid3DAnnotationTable(SQLModel, table=True):
    """Database table model for 3D cuboid annotations."""

    __tablename__ = "cuboid_3d_annotation"

    sample_id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        foreign_key="annotation_base.sample_id",
    )

    frame_id: str
    px: float
    py: float
    pz: float
    qx: float
    qy: float
    qz: float
    qw: float
    sx: float
    sy: float
    sz: float
    interpolated: bool = False

    annotation_base: Mapped["AnnotationBaseTable"] = Relationship(
        back_populates="cuboid_3d_details"
    )


class Cuboid3DAnnotationView(SQLModel):
    """API response model for 3D cuboid annotations."""

    frame_id: str
    px: float
    py: float
    pz: float
    qx: float
    qy: float
    qz: float
    qw: float
    sx: float
    sy: float
    sz: float
    interpolated: bool = False
