"""Read one sensor calibration slot for an MCAP bag."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.sensor_calibration import SensorCalibrationTable


def get_by_recording_collection_id(
    session: Session, recording_id: UUID, collection_id: UUID
) -> SensorCalibrationTable | None:
    """Return the calibration for one camera slot (``collection_id``) on a bag, if any."""
    return session.exec(
        select(SensorCalibrationTable).where(
            col(SensorCalibrationTable.recording_id) == recording_id,
            col(SensorCalibrationTable.collection_id) == collection_id,
        )
    ).one_or_none()
