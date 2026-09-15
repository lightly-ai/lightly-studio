"""Per-recording camera intrinsics."""

from uuid import UUID, uuid4

from sqlalchemy import ARRAY, Float, UniqueConstraint
from sqlmodel import Column, Field, SQLModel

_K_LENGTH = 9


class SensorCalibrationBase(SQLModel):
    """Shared fields for a single camera's calibration on a recording."""

    width: int = Field(gt=0)
    """Image width in pixels."""
    height: int = Field(gt=0)
    """Image height in pixels."""


class SensorCalibrationCreate(SensorCalibrationBase):
    """Input model for inserting a sensor calibration row."""

    recording_id: UUID
    collection_id: UUID
    """Must be an MCAP group component definition with ``mcap_data_type=video_frame``."""
    k: list[float] = Field(min_length=_K_LENGTH, max_length=_K_LENGTH)
    """Row-major ``camera_info.k`` (3x3 intrinsics matrix), length 9."""


class SensorCalibrationTable(SensorCalibrationBase, table=True):
    """One row per camera calibration slot on a recording."""

    __tablename__ = "sensor_calibration"
    __table_args__ = (
        UniqueConstraint(
            "recording_id",
            "collection_id",
            name="unique_sensor_calibration_slot_per_recording",
        ),
    )

    sensor_calibration_id: UUID = Field(default_factory=uuid4, primary_key=True)
    recording_id: UUID = Field(foreign_key="recording.recording_id", index=True)
    collection_id: UUID = Field(foreign_key="mcap_group_component_definition.collection_id")
    k: list[float] = Field(sa_column=Column(ARRAY(Float), nullable=False))
