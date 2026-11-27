"""Tests for the ego position of one tick of an MCAP sequence."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from pytest_mock import MockerFixture, MockType
from sqlmodel import Session

from lightly_studio.core.mcap.errors import TransformNotFoundError
from lightly_studio.models.mcap_sequence_ticks import EgoPositionFrames
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import group_resolver
from lightly_studio.services import recording_service
from tests.resolvers.mcap_group_sequence_resolver import helpers
from tests.resolvers.mcap_group_sequence_resolver.helpers import McapSequenceFixture

_TIMESTAMP_NS = 1_000


def test_get_tick_ego_position(db_session: Session, mocker: MockerFixture) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)
    _add_tick(session=db_session, fixture=fixture, timestamp_ns=_TIMESTAMP_NS)
    ego_to_map = np.eye(4)
    ego_to_map[:3, 3] = [12.0, -3.0, 0.5]
    transform = _patch_transforms(mocker=mocker, return_value=ego_to_map)

    result = recording_service.get_tick_ego_position(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
        seq_number=0,
        frames=EgoPositionFrames(target_frame_id="map", ego_frame_id="CABIN"),
    )

    assert result is not None
    assert result.position == [12.0, -3.0, 0.5]
    transform.assert_called_once_with(
        reader=mocker.ANY,
        source_frame_id="CABIN",
        target_frame_id="map",
        timestamp_ns=_TIMESTAMP_NS,
        static_transforms=[],
        dynamic_transforms=[],
    )


def test_get_tick_ego_position__same_frame(db_session: Session, mocker: MockerFixture) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)
    _add_tick(session=db_session, fixture=fixture, timestamp_ns=_TIMESTAMP_NS)
    transform = _patch_transforms(mocker=mocker, return_value=np.eye(4))

    result = recording_service.get_tick_ego_position(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
        seq_number=0,
        frames=EgoPositionFrames(target_frame_id="CABIN", ego_frame_id="CABIN"),
    )

    assert result is not None
    assert result.position == [0.0, 0.0, 0.0]
    transform.assert_not_called()


def test_get_tick_ego_position__transform_not_found(
    db_session: Session, mocker: MockerFixture
) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)
    _add_tick(session=db_session, fixture=fixture, timestamp_ns=_TIMESTAMP_NS)
    transform = _patch_transforms(mocker=mocker, return_value=None)
    transform.side_effect = TransformNotFoundError("No transform from CABIN to map.")

    result = recording_service.get_tick_ego_position(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
        seq_number=0,
        frames=EgoPositionFrames(target_frame_id="map", ego_frame_id="CABIN"),
    )

    assert result is not None
    assert result.position is None


def test_get_tick_ego_position__no_timestamp(db_session: Session, mocker: MockerFixture) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)
    _add_tick(session=db_session, fixture=fixture, timestamp_ns=None)
    transform = _patch_transforms(mocker=mocker, return_value=np.eye(4))

    result = recording_service.get_tick_ego_position(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
        seq_number=0,
        frames=EgoPositionFrames(target_frame_id="map", ego_frame_id="CABIN"),
    )

    assert result is not None
    assert result.position is None
    transform.assert_not_called()


def test_get_tick_ego_position__tick_not_found(db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)

    result = recording_service.get_tick_ego_position(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
        seq_number=5,
        frames=EgoPositionFrames(target_frame_id="map", ego_frame_id="CABIN"),
    )

    assert result is None


def _add_tick(session: Session, fixture: McapSequenceFixture, timestamp_ns: int | None) -> None:
    group_id = group_resolver.create_many(
        session=session,
        collection_id=fixture.group_collection.collection_id,
        groups=[set()],
    )[0]
    session.add(
        SampleSequenceLinkTable(
            sample_id=group_id,
            sequence_sample_id=fixture.sample_id,
            seq_number=0,
            timestamp_ns=timestamp_ns,
        )
    )
    session.commit()


def _patch_transforms(mocker: MockerFixture, return_value: NDArray[np.float64] | None) -> MockType:
    mocker.patch.object(recording_service.reader_cache, "borrow_reader")
    mocker.patch.object(
        recording_service.load_static_transforms, "load_static_transforms", return_value=[]
    )
    mocker.patch.object(
        recording_service.load_dynamic_transforms,
        "load_dynamic_transforms_near",
        return_value=[],
    )
    return mocker.patch.object(
        recording_service.transform_to_target_frame,
        "transform_to_target_frame",
        return_value=return_value,
    )
