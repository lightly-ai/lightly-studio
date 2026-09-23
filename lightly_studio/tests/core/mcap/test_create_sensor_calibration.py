from __future__ import annotations

from uuid import UUID

from lightly_studio.core.mcap.create_sensor_calibration import CreateSensorCalibration
from lightly_studio.core.mcap.type_definitions import CameraIntrinsics


class TestCreateSensorCalibration:
    def test_from_camera_intrinsics(self) -> None:
        collection_id = UUID("00000000-0000-0000-0000-000000000001")
        intrinsics = CameraIntrinsics(
            width=640,
            height=480,
            camera_matrix=(600.0, 0.0, 320.0, 0.0, 600.0, 240.0, 0.0, 0.0, 1.0),
            frame_id="cam_front",
            distortion_model="plumb_bob",
            distortion_coefficients=(0.1, 0.0, 0.0, 0.0, 0.0),
        )

        calibration = CreateSensorCalibration.from_camera_intrinsics(
            collection_id=collection_id, intrinsics=intrinsics
        )

        assert calibration == CreateSensorCalibration(
            collection_id=collection_id,
            width=640,
            height=480,
            k=(600.0, 0.0, 320.0, 0.0, 600.0, 240.0, 0.0, 0.0, 1.0),
        )
