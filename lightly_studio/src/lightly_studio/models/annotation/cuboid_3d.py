"""3D cuboid annotation models.

A cuboid is a 9-DoF box (centre, size, quaternion) expressed in a named
coordinate frame. It is parented to a tick group, not to a single sensor.
"""

import math
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pydantic
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from lightly_studio.models.annotation.annotation_base import (
        AnnotationBaseTable,
    )
else:
    AnnotationBaseTable = object

_QUATERNION_UNIT_TOLERANCE = 1e-6


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

    @pydantic.model_validator(mode="after")
    def _validate(self) -> "Cuboid3DCreate":  # noqa: N804
        floats = (
            self.px,
            self.py,
            self.pz,
            self.qx,
            self.qy,
            self.qz,
            self.qw,
            self.sx,
            self.sy,
            self.sz,
        )
        if not all(math.isfinite(v) for v in floats):
            raise ValueError("All cuboid float fields must be finite.")
        if self.sx <= 0 or self.sy <= 0 or self.sz <= 0:
            raise ValueError("Cuboid size dimensions sx, sy, sz must each be positive.")
        norm = math.sqrt(self.qx**2 + self.qy**2 + self.qz**2 + self.qw**2)
        if abs(norm - 1.0) > _QUATERNION_UNIT_TOLERANCE:
            raise ValueError("Cuboid quaternion must be a unit quaternion.")
        return self


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
