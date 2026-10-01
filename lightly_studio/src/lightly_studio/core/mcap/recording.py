"""A single recording of an MCAP dataset."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.mcap.create_sensor_calibration import CreateSensorCalibration
from lightly_studio.core.mcap.type_definitions import StaticTransform
from lightly_studio.models.recording import RecordingFormat, RecordingTable
from lightly_studio.models.sensor_calibration import SensorCalibrationCreate
from lightly_studio.models.static_transform import StaticTransformCreate
from lightly_studio.resolvers import sensor_calibration_resolver, static_transform_resolver


class Recording:
    """One recording of a dataset, e.g. a single `.mcap` file.

    The recording owns where its bytes are and everything that describes the run that
    produced them, such as the calibration of its cameras and the static transforms
    between its coordinate frames. Its groups and their order
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

    def add_static_transforms(self, transforms: Sequence[StaticTransform]) -> list[UUID]:
        """Add the static transforms between the coordinate frames of the recording.

        One edge per child frame. A later edge for the same child replaces the earlier
        one before this is called.

        Args:
            transforms: The static transforms to add, one per child frame.

        Returns:
            The IDs of the added transforms, in the order of `transforms`.

        Raises:
            ValueError: If `transforms` is empty, or a frame id is empty.
            sqlalchemy.exc.IntegrityError: If an edge is already stored for this
                recording.
        """
        return static_transform_resolver.create_many(
            session=self._session,
            rows=[
                _static_transform_create(recording_id=self.recording_id, transform=transform)
                for transform in transforms
            ],
        )

    def set_reference_frame_ids(self, frame_ids: Sequence[str]) -> None:
        """Store the frames the scene of this recording can be shown in.

        The first frame is the default. The order is the order of the Frame menu.

        Args:
            frame_ids: The coordinate frame ids, in display order.
        """
        self._inner.reference_frame_ids = list(frame_ids)
        self._session.add(self._inner)
        self._session.commit()
        self._session.refresh(self._inner)


def _static_transform_create(
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
