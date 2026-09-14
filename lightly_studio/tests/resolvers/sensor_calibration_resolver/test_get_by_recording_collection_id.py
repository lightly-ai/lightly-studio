"""Tests for reading a single sensor calibration slot."""

from sqlmodel import Session

from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.models.sensor_calibration import SensorCalibrationCreate
from lightly_studio.resolvers import (
    mcap_group_component_definition_resolver,
    sensor_calibration_resolver,
)
from tests.resolvers.mcap_group_component_definition_resolver.helpers import (
    create_mcap_group_components,
)
from tests.resolvers.sensor_calibration_resolver.helpers import K, create_recording


def test_get_by_recording_collection_id(db_session: Session) -> None:
    recording_id = create_recording(session=db_session)
    _, children = create_mcap_group_components(session=db_session)
    front = mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=children["image"].collection_id,
        mcap_data_type=McapDataType.VIDEO_FRAME,
        channel_id=3,
    )
    other = mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=children["point_cloud"].collection_id,
        mcap_data_type=McapDataType.POINT_CLOUD,
        channel_id=5,
    )
    sensor_calibration_resolver.create_many(
        session=db_session,
        rows=[
            SensorCalibrationCreate(
                recording_id=recording_id, collection_id=front, width=1920, height=1080, k=K
            ),
        ],
    )

    row = sensor_calibration_resolver.get_by_recording_collection_id(
        session=db_session, recording_id=recording_id, collection_id=front
    )

    assert row is not None
    assert row.collection_id == front
    assert row.k == K
    assert (
        sensor_calibration_resolver.get_by_recording_collection_id(
            session=db_session, recording_id=recording_id, collection_id=other
        )
        is None
    )
