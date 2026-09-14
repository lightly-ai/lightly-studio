"""Per-recording ``/tf_static`` edges.

One row per static transform edge (child -> parent, ROS ``TransformStamped``) on the recording.
Edges are keyed by frame name strings.
"""

from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class StaticTransformBase(SQLModel):
    """Shared fields for a single static transform edge on a recording."""

    parent: str
    """Parent frame name."""
    child: str
    """Child frame name."""
    qx: float
    qy: float
    qz: float
    qw: float
    tx: float
    ty: float
    tz: float


class StaticTransformCreate(StaticTransformBase):
    """Input model for inserting a static transform row."""

    recording_id: UUID


class StaticTransformTable(StaticTransformBase, table=True):
    """One row per ``/tf_static`` edge on a recording."""

    __tablename__ = "static_transform"
    __table_args__ = (
        UniqueConstraint(
            "recording_id",
            "parent",
            "child",
            name="unique_static_transform_edge_per_recording",
        ),
    )

    static_transform_id: UUID = Field(default_factory=uuid4, primary_key=True)
    recording_id: UUID = Field(foreign_key="recording.recording_id", index=True)
