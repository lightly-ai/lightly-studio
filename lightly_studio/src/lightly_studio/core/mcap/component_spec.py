"""The spec of one component of an MCAP dataset, without database access."""

from __future__ import annotations

from dataclasses import dataclass

from lightly_studio.models.mcap_group_component_definition import McapDataType


@dataclass(frozen=True)
class McapComponentSpec:
    """One component of an MCAP dataset, and the topics it is filled from.

    The dataset is declared with one spec per sensor, and every recording indexed into
    it is read through the same specs:

    ```python
    ls.McapComponentSpec(
        name="front",
        mcap_data_type=ls.McapDataType.VIDEO_FRAME,
        topic="/cam/front/compressed_video",
        camera_info_topic="/cam/front/camera_info",
    )
    ls.McapComponentSpec(
        name="pcl_front",
        mcap_data_type=ls.McapDataType.POINT_CLOUD,
        topic="/lidar/points",
        frame_id="livox_front_left",
    )
    ```
    """

    name: str
    """The name the component is shown and looked up under, e.g. `"front"`."""
    mcap_data_type: McapDataType
    """Whether the component carries video frames or point clouds."""
    topic: str
    """The MCAP topic the data is read from, e.g. `"/cam/front/compressed_video"`."""
    camera_info_topic: str | None = None
    """The topic the calibration of a camera is published on. `None` for a lidar."""
    frame_id: str | None = None
    """The coordinate frame the data is in.

    Set it for a lidar, whose frame is part of the message payload and is not read. The
    frame of a camera comes from its camera info topic instead.
    """

    @property
    def is_camera(self) -> bool:
        """Whether the component is a camera. A lidar sets `frame_id` instead."""
        return self.camera_info_topic is not None
