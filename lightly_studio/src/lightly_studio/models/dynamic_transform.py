"""Per-recording ``/tf`` edges.

One row per dynamic transform edge (child -> parent, ROS ``TransformStamped``) at one
capture time. The same parent and child repeat as the pose changes.
"""

from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Index
from sqlmodel import Field, SQLModel


class DynamicTransformBase(SQLModel):
    """Shared fields for one dynamic transform edge at one capture time."""

    parent: str
    """Parent frame name."""
    child: str
    """Child frame name."""
    timestamp_ns: int
    """Capture time of the edge, from ``header.stamp`` or ``timestamp``."""
    qx: float
    qy: float
    qz: float
    qw: float
    tx: float
    ty: float
    tz: float


class DynamicTransformCreate(DynamicTransformBase):
    """Input model for inserting a dynamic transform row."""

    recording_id: UUID


class DynamicTransformTable(DynamicTransformBase, table=True):
    """One ``/tf`` edge of a recording at one capture time."""

    __tablename__ = "dynamic_transform"
    __table_args__ = (
        Index(
            "ix_dynamic_transform_recording_id_timestamp_ns",
            "recording_id",
            "timestamp_ns",
        ),
    )

    dynamic_transform_id: UUID = Field(default_factory=uuid4, primary_key=True)
    # BigInteger: epoch nanoseconds overflow a 32-bit INTEGER on PostgreSQL.
    timestamp_ns: int = Field(sa_type=BigInteger)
    recording_id: UUID = Field(foreign_key="recording.recording_id")
