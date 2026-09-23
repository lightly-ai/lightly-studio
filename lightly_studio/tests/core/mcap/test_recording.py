from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from lightly_studio.core.mcap.create_sensor_calibration import CreateSensorCalibration
from lightly_studio.core.mcap.recording import Recording
from lightly_studio.models.collection import SampleType
from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.resolvers import (
    collection_resolver,
    mcap_group_component_definition_resolver,
    recording_resolver,
    sensor_calibration_resolver,
)
from tests.helpers_resolvers import create_collection

CAMERA_MATRIX = [600.0, 0.0, 320.0, 0.0, 600.0, 240.0, 0.0, 0.0, 1.0]


class TestRecording:
    def test_properties(self, db_session: Session) -> None:
        recording = _create_recording(session=db_session, uri="/data/perception.mcap")

        assert recording.uri == "/data/perception.mcap"
        assert recording.recording_format == RecordingFormat.MCAP

    def test_add_sensor_calibrations(self, db_session: Session) -> None:
        recording = _create_recording(session=db_session, uri="/data/perception.mcap")
        front = _create_component_collection_id(
            session=db_session, name="front", mcap_data_type=McapDataType.VIDEO_FRAME
        )

        calibration_ids = recording.add_sensor_calibrations(
            calibrations=[
                CreateSensorCalibration(collection_id=front, width=640, height=480, k=CAMERA_MATRIX)
            ]
        )

        assert len(calibration_ids) == 1
        calibrations = sensor_calibration_resolver.get_all_by_recording_id(
            session=db_session, recording_id=recording.recording_id
        )
        assert len(calibrations) == 1
        assert calibrations[0].collection_id == front
        assert calibrations[0].width == 640
        assert calibrations[0].height == 480
        assert calibrations[0].k == CAMERA_MATRIX

    def test_add_sensor_calibrations__empty(self, db_session: Session) -> None:
        recording = _create_recording(session=db_session, uri="/data/perception.mcap")

        with pytest.raises(ValueError, match="rows must be non-empty"):
            recording.add_sensor_calibrations(calibrations=[])

    def test_add_sensor_calibrations__point_cloud_component(self, db_session: Session) -> None:
        recording = _create_recording(session=db_session, uri="/data/perception.mcap")
        pcl_front = _create_component_collection_id(
            session=db_session, name="pcl_front", mcap_data_type=McapDataType.POINT_CLOUD
        )

        with pytest.raises(ValueError, match="requires a 'video_frame' slot"):
            recording.add_sensor_calibrations(
                calibrations=[
                    CreateSensorCalibration(
                        collection_id=pcl_front, width=640, height=480, k=CAMERA_MATRIX
                    )
                ]
            )

    def test_add_sensor_calibrations__component_twice(self, db_session: Session) -> None:
        recording = _create_recording(session=db_session, uri="/data/perception.mcap")
        front = _create_component_collection_id(
            session=db_session, name="front", mcap_data_type=McapDataType.VIDEO_FRAME
        )
        calibration = CreateSensorCalibration(
            collection_id=front, width=640, height=480, k=CAMERA_MATRIX
        )
        recording.add_sensor_calibrations(calibrations=[calibration])

        with pytest.raises(IntegrityError):
            recording.add_sensor_calibrations(calibrations=[calibration])
        db_session.rollback()


def _create_recording(session: Session, uri: str) -> Recording:
    """Create a recording on a fresh dataset, and wrap it."""
    collection = create_collection(session=session, sample_type=SampleType.SEQUENCE)
    recording_id = recording_resolver.create(
        session=session,
        dataset_id=collection.dataset_id,
        uri=uri,
        format_=RecordingFormat.MCAP,
    )
    inner = recording_resolver.get_by_id(session=session, recording_id=recording_id)
    assert inner is not None
    return Recording(session=session, inner=inner)


def _create_component_collection_id(
    session: Session, name: str, mcap_data_type: McapDataType
) -> UUID:
    """Create one MCAP component collection with its definition, and return its ID."""
    group_collection = create_collection(session=session, sample_type=SampleType.GROUP)
    component_collections = collection_resolver.create_group_components(
        session=session,
        parent_collection_id=group_collection.collection_id,
        components=[(name, SampleType.MCAP)],
    )
    collection_id = component_collections[name].collection_id
    mcap_group_component_definition_resolver.create(
        session=session, collection_id=collection_id, mcap_data_type=mcap_data_type
    )
    return collection_id
