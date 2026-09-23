"""A single recording of an MCAP dataset."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.mcap.create_sensor_calibration import CreateSensorCalibration
from lightly_studio.models.recording import RecordingFormat, RecordingTable
from lightly_studio.models.sensor_calibration import SensorCalibrationCreate
from lightly_studio.resolvers import sensor_calibration_resolver


class Recording:
    """One recording of a dataset, e.g. a single `.mcap` file.

    The recording owns where its bytes are and everything that describes the run that
    produced them, such as the calibration of its cameras. Its groups and their order
    live on a sequence instead, which points at the recording it was indexed from.
    """

    def __init__(self, session: Session, inner: RecordingTable) -> None:
        """Initialize the recording.

        Args:
            session: Database session for resolver operations.
            inner: The recording row the object reads its fields from.
        """
        self._session = session
        self._inner = inner

    @property
    def recording_id(self) -> UUID:
        """The ID of the recording."""
        return self._inner.recording_id

    @property
    def uri(self) -> str:
        """Where the bytes of the recording are, e.g. a path or an `s3://` URI."""
        return self._inner.uri

    @property
    def recording_format(self) -> RecordingFormat:
        """The format of the recording."""
        return self._inner.format

    def add_sensor_calibrations(
        self, calibrations: Sequence[CreateSensorCalibration]
    ) -> list[UUID]:
        """Add the intrinsic calibration of one or more cameras of the recording.

        A component has at most one calibration per recording.

        Args:
            calibrations: The calibrations to add, one per camera component.

        Returns:
            The IDs of the added calibrations, in the order of `calibrations`.

        Raises:
            ValueError: If `calibrations` is empty, or if a component does not carry
                video frames.
            sqlalchemy.exc.IntegrityError: If a component already has a calibration on
                this recording.
        """
        return sensor_calibration_resolver.create_many(
            session=self._session,
            rows=[
                SensorCalibrationCreate(
                    recording_id=self.recording_id,
                    collection_id=calibration.collection_id,
                    width=calibration.width,
                    height=calibration.height,
                    k=list(calibration.k),
                )
                for calibration in calibrations
            ],
        )
