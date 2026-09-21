"""Class for creating the calibration of one camera component of a recording."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from lightly_studio.core.mcap.type_definitions import CameraIntrinsics


@dataclass(frozen=True)
class CreateSensorCalibration:
    """The intrinsic calibration of one camera component of a recording.

    Every recording has its own calibration, so it is added to the recording and not to
    the component. Build it from what the MCAP reader reports for the camera info topic
    of the component:

    ```python
    intrinsics = reader.get_intrinsic(topic="/front/camera_info")
    calibration = ls.CreateSensorCalibration.from_camera_intrinsics(
        collection_id=front.collection_id, intrinsics=intrinsics
    )
    ```
    """

    collection_id: UUID
    """The component the calibration belongs to. Must carry video frames."""
    width: int
    """The image width in pixels."""
    height: int
    """The image height in pixels."""
    k: Sequence[float]
    """The 3x3 camera matrix K in row-major order, 9 values."""

    @classmethod
    def from_camera_intrinsics(
        cls, collection_id: UUID, intrinsics: CameraIntrinsics
    ) -> CreateSensorCalibration:
        """Build the calibration of a component from what the MCAP reader reported.

        Args:
            collection_id: The camera component the calibration belongs to, e.g.
                `front.collection_id`.
            intrinsics: The intrinsics of a single camera, from
                `McapFileReader.get_intrinsic`.

        Returns:
            The calibration to add to the recording the intrinsics were read from.
        """
        return cls(
            collection_id=collection_id,
            width=intrinsics.width,
            height=intrinsics.height,
            k=intrinsics.camera_matrix,
        )
