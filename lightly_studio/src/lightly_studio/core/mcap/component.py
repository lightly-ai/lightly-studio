"""One named component of the groups of an MCAP dataset."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.mcap_group_component_definition import (
    McapDataType,
    McapGroupComponentDefinitionTable,
)
from lightly_studio.resolvers import mcap_group_component_definition_resolver


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


class McapComponent:
    """A component of the groups of an MCAP dataset, e.g. one camera or one lidar.

    The component holds what stays the same over all recordings of the dataset: which
    kind of data it carries, which MCAP channel it is read from, and which coordinate
    frame its data is in. The channel and the frame are unknown until the first
    recording is indexed:

    ```python
    front = group_dataset.get_component("front")
    front.update_mcap_definition(channel_id=frames[0].channel_id, frame_id="cam_front")
    print(front.channel_id, front.frame_id)
    ```
    """

    def __init__(self, session: Session, collection_id: UUID, name: str) -> None:
        """Initialize the component.

        Args:
            session: Database session for resolver operations.
            collection_id: The ID of the component collection, which is also the ID of
                its MCAP component definition.
            name: The name of the component in the group schema, e.g. `"front"`.
        """
        self._session = session
        self._collection_id = collection_id
        self._name = name

    @property
    def name(self) -> str:
        """The name of the component in the group schema."""
        return self._name

    @property
    def collection_id(self) -> UUID:
        """The ID of the component collection.

        It is also the ID the calibration of a camera component refers to.
        """
        return self._collection_id

    @property
    def mcap_data_type(self) -> McapDataType:
        """Whether the component carries video frames or point clouds."""
        return self._definition().mcap_data_type

    @property
    def channel_id(self) -> int | None:
        """The MCAP channel the component is read from.

        `None` until the first recording is indexed.
        """
        return self._definition().channel_id

    @property
    def frame_id(self) -> str | None:
        """The coordinate frame the data of the component is in.

        `None` until the first recording is indexed, or if the recording names no frame.
        """
        return self._definition().frame_id

    def update_mcap_definition(
        self, channel_id: int | None = None, frame_id: str | None = None
    ) -> None:
        """Fill the channel and the frame of the component from a recording.

        The first recording that is indexed fills them. A later recording does not
        change them, so that all recordings of a dataset keep one schema. An argument
        that is `None` leaves its value untouched.

        Args:
            channel_id: The MCAP channel of the component, e.g.
                `locators[0].channel_id`.
            frame_id: The coordinate frame of the data, e.g. `intrinsics.frame_id` for a
                camera.
        """
        mcap_group_component_definition_resolver.update(
            session=self._session,
            collection_id=self._collection_id,
            channel_id=channel_id,
            frame_id=frame_id,
        )

    def _definition(self) -> McapGroupComponentDefinitionTable:
        definition = mcap_group_component_definition_resolver.get_by_collection_id(
            session=self._session, collection_id=self._collection_id
        )
        if definition is None:
            raise RuntimeError(f"Component '{self._name}' has no MCAP component definition.")
        return definition
