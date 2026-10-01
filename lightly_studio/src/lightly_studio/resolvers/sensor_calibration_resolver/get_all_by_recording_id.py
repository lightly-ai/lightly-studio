"""Read all sensor calibrations for an MCAP bag."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.sensor_calibration import SensorCalibrationTable


def get_all_by_recording_id(session: Session, recording_id: UUID) -> list[SensorCalibrationTable]:
    """Return every sensor calibration row for a bag."""
    return list(
        session.exec(
            select(SensorCalibrationTable).where(
                col(SensorCalibrationTable.recording_id) == recording_id
            )
        ).all()
    )
