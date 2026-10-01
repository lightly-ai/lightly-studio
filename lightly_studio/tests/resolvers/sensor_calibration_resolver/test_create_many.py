"""Tests for creating sensor calibrations."""

import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
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


def test_create_many(db_session: Session) -> None:
    recording_id = create_recording(session=db_session)
    _, children = create_mcap_group_components(session=db_session)
    front = mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=children["image"].collection_id,
        mcap_data_type=McapDataType.VIDEO_FRAME,
        channel_id=3,
        frame_id="main",
    )

    ids = sensor_calibration_resolver.create_many(
        session=db_session,
        rows=[
            SensorCalibrationCreate(
                recording_id=recording_id,
                collection_id=front,
                width=1920,
                height=1080,
                k=K,
            ),
        ],
    )

    assert len(ids) == 1
    rows = sensor_calibration_resolver.get_all_by_recording_id(
        session=db_session, recording_id=recording_id
    )
    assert len(rows) == 1
    assert rows[0].sensor_calibration_id == ids[0]
    assert rows[0].collection_id == front
    assert rows[0].k == K
    assert rows[0].width == 1920
    assert rows[0].height == 1080


def test_create_many__k_must_have_length_9() -> None:
    with pytest.raises(ValidationError):
        SensorCalibrationCreate(
            recording_id=uuid.uuid4(),
            collection_id=uuid.uuid4(),
            width=1920,
            height=1080,
            k=[1.0] * 8,
        )


def test_create_many__unique_slot(db_session: Session) -> None:
    recording_id = create_recording(session=db_session)
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

    with pytest.raises(IntegrityError):
        sensor_calibration_resolver.create_many(
            session=db_session,
            rows=[
                SensorCalibrationCreate(
                    recording_id=recording_id, collection_id=front, width=640, height=480, k=K
                ),
            ],
        )
    db_session.rollback()


def test_create_many__missing_recording(db_session: Session) -> None:
    _, children = create_mcap_group_components(session=db_session)
    front = mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=children["image"].collection_id,
        mcap_data_type=McapDataType.VIDEO_FRAME,
        channel_id=3,
    )

    with pytest.raises(ValueError, match=r"Recording with id .* not found"):
        sensor_calibration_resolver.create_many(
            session=db_session,
            rows=[
                SensorCalibrationCreate(
                    recording_id=uuid.uuid4(),
                    collection_id=front,
                    width=1920,
                    height=1080,
                    k=K,
                ),
            ],
        )


def test_create_many__missing_mcap_gcd(db_session: Session) -> None:
    recording_id = create_recording(session=db_session)

    with pytest.raises(ValueError, match=r"McapGroupComponentDefinition .* not found"):
        sensor_calibration_resolver.create_many(
            session=db_session,
            rows=[
                SensorCalibrationCreate(
                    recording_id=recording_id,
                    collection_id=uuid.uuid4(),
                    width=1920,
                    height=1080,
                    k=K,
                ),
            ],
        )


def test_create_many__rejects_pointcloud_slot(db_session: Session) -> None:
    recording_id = create_recording(session=db_session)
    _, children = create_mcap_group_components(session=db_session)
    lidar = mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=children["point_cloud"].collection_id,
        mcap_data_type=McapDataType.POINT_CLOUD,
        channel_id=5,
    )

    with pytest.raises(ValueError, match="requires a 'video_frame' slot"):
        sensor_calibration_resolver.create_many(
            session=db_session,
            rows=[
                SensorCalibrationCreate(
                    recording_id=recording_id,
                    collection_id=lidar,
                    width=1920,
                    height=1080,
                    k=K,
                ),
            ],
        )


def test_create_many__empty_rows(db_session: Session) -> None:
    with pytest.raises(ValueError, match="rows must be non-empty"):
        sensor_calibration_resolver.create_many(session=db_session, rows=[])
