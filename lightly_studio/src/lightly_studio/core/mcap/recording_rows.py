"""Rows that describe a recording, built from the values read from an MCAP file."""

from __future__ import annotations

from uuid import UUID

from lightly_studio.core.mcap.create_sensor_calibration import CreateSensorCalibration
from lightly_studio.core.mcap.type_definitions import StaticTransform
from lightly_studio.models.dynamic_transform import DynamicTransformCreate
from lightly_studio.models.sensor_calibration import SensorCalibrationCreate
from lightly_studio.models.static_transform import StaticTransformCreate


def sensor_calibration_create(
    recording_id: UUID, calibration: CreateSensorCalibration
) -> SensorCalibrationCreate:
    """Build the row of the calibration of one camera."""
    return SensorCalibrationCreate(
        recording_id=recording_id,
        collection_id=calibration.collection_id,
        width=calibration.width,
        height=calibration.height,
        k=list(calibration.k),
    )


def static_transform_create(
    recording_id: UUID, transform: StaticTransform
) -> StaticTransformCreate:
    """Build the row of one static transform edge."""
    qx, qy, qz, qw = transform.rotation
    tx, ty, tz = transform.translation
    return StaticTransformCreate(
        recording_id=recording_id,
        parent=transform.parent_frame_id,
        child=transform.child_frame_id,
        qx=qx,
        qy=qy,
        qz=qz,
        qw=qw,
        tx=tx,
        ty=ty,
        tz=tz,
    )


def dynamic_transform_create(
    recording_id: UUID, transform: StaticTransform
) -> DynamicTransformCreate:
    """Build the row of one dynamic transform edge."""
    qx, qy, qz, qw = transform.rotation
    tx, ty, tz = transform.translation
    return DynamicTransformCreate(
        recording_id=recording_id,
        parent=transform.parent_frame_id,
        child=transform.child_frame_id,
        timestamp_ns=transform.timestamp_ns,
        qx=qx,
        qy=qy,
        qz=qz,
        qw=qw,
        tx=tx,
        ty=ty,
        tz=tz,
    )
