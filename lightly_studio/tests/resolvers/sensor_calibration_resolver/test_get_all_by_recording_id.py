"""Tests for reading sensor calibrations."""

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


def test_get_all_by_recording_id(db_session: Session) -> None:
    recording_id = create_recording(session=db_session)
    other_recording_id = create_recording(session=db_session)
    _, children = create_mcap_group_components(session=db_session)
    front = mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=children["image"].collection_id,
        mcap_data_type=McapDataType.VIDEO_FRAME,
        channel_id=3,
    )
    sensor_calibration_resolver.create_many(
        session=db_session,
        rows=[
            SensorCalibrationCreate(
                recording_id=recording_id, collection_id=front, width=1920, height=1080, k=K
            ),
        ],
    )
    _, other_children = create_mcap_group_components(session=db_session)
    other_front = mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=other_children["image"].collection_id,
        mcap_data_type=McapDataType.VIDEO_FRAME,
        channel_id=3,
    )
    sensor_calibration_resolver.create_many(
        session=db_session,
        rows=[
            SensorCalibrationCreate(
                recording_id=other_recording_id,
                collection_id=other_front,
                width=1920,
                height=1080,
                k=K,
            ),
        ],
    )

    rows = sensor_calibration_resolver.get_all_by_recording_id(
        session=db_session, recording_id=recording_id
    )

    assert len(rows) == 1
    assert rows[0].recording_id == recording_id
    assert rows[0].collection_id == front
