from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image
from pytest_mock import MockerFixture

from lightly_studio.core.mcap import add_mcaps, compressed_video
from lightly_studio.core.mcap.component import McapComponentSpec
from lightly_studio.core.mcap.mcap_dataset import McapDataset
from lightly_studio.database import db_manager
from lightly_studio.embed import embed_mcap_sequences
from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.models.mcap_group_sequence import McapSequenceKeyframe
from lightly_studio.resolvers import (
    collection_embedding_model_resolver,
    sample_embedding_resolver,
)
from tests.core.mcap import helpers

VIDEO_COMPONENT = "front"
POINT_CLOUD_COMPONENT = "pcl_front"

VIDEO_SPEC = McapComponentSpec(
    name=VIDEO_COMPONENT,
    mcap_data_type=McapDataType.VIDEO_FRAME,
    topic=helpers.CAMERA_VIDEO_TOPIC,
    camera_info_topic=helpers.CAMERA_INFO_TOPIC,
)
POINT_CLOUD_SPEC = McapComponentSpec(
    name=POINT_CLOUD_COMPONENT,
    mcap_data_type=McapDataType.POINT_CLOUD,
    topic=helpers.LIDAR_POINTS_TOPIC,
    frame_id=helpers.LIDAR_FRAME_ID,
)


def test_embed_mcap_sequences(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    components = [VIDEO_SPEC, POINT_CLOUD_SPEC]
    dataset = McapDataset.create(components=components, name="perception")
    # Every video frame is a tick, so the sequence holds both keyframes of the recording.
    sequence_sample_id = add_mcaps.index_recording(
        dataset=dataset,
        mcap_path=str(helpers.write_mcap(tmp_path / "recording.mcap")),
        sync_component=VIDEO_COMPONENT,
        components=components,
    )
    # The test recording holds no decodable video, so decoding returns a fixed image.
    to_image = mocker.patch.object(
        compressed_video,
        "to_image",
        return_value=Image.new(mode="RGB", size=(2, 2)),
    )
    session = db_manager.persistent_session()

    embed_mcap_sequences.embed_mcap_sequences(
        session=session,
        collection_id=dataset.collection_id,
        sequence_sample_ids=[sequence_sample_id],
        frames_per_sequence=8,
    )

    # The recording has 2 keyframes, fewer than 8, so both are decoded.
    assert to_image.call_count == len(helpers.VIDEO_KEYFRAME_LOG_TIMES_NS)
    model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=session, collection_id=dataset.collection_id
    )
    assert model_id is not None
    rows = sample_embedding_resolver.get_by_sample_ids(
        session=session, sample_ids=[sequence_sample_id], embedding_model_id=model_id
    )
    assert [row.sample_id for row in rows] == [sequence_sample_id]


def test_embed_mcap_sequences__samples_frames_per_sequence(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    components = [VIDEO_SPEC, POINT_CLOUD_SPEC]
    dataset = McapDataset.create(components=components, name="perception")
    sequence_sample_id = add_mcaps.index_recording(
        dataset=dataset,
        mcap_path=str(helpers.write_mcap(tmp_path / "recording.mcap")),
        sync_component=VIDEO_COMPONENT,
        components=components,
    )
    to_image = mocker.patch.object(
        compressed_video,
        "to_image",
        return_value=Image.new(mode="RGB", size=(2, 2)),
    )

    embed_mcap_sequences.embed_mcap_sequences(
        session=db_manager.persistent_session(),
        collection_id=dataset.collection_id,
        sequence_sample_ids=[sequence_sample_id],
        frames_per_sequence=1,
    )

    assert to_image.call_count == 1


def test_embed_mcap_sequences__no_camera_component(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    components = [POINT_CLOUD_SPEC]
    dataset = McapDataset.create(components=components, name="perception")
    sequence_sample_id = add_mcaps.index_recording(
        dataset=dataset,
        mcap_path=str(helpers.write_mcap(tmp_path / "recording.mcap")),
        sync_component=POINT_CLOUD_COMPONENT,
        components=components,
    )
    session = db_manager.persistent_session()

    with caplog.at_level(level=logging.WARNING):
        embed_mcap_sequences.embed_mcap_sequences(
            session=session,
            collection_id=dataset.collection_id,
            sequence_sample_ids=[sequence_sample_id],
        )

    assert "no camera component" in caplog.text
    assert (
        collection_embedding_model_resolver.get_default_by_collection_id(
            session=session, collection_id=dataset.collection_id
        )
        is None
    )


def test_embed_mcap_sequences__undecodable_frames_store_no_embedding(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    components = [VIDEO_SPEC, POINT_CLOUD_SPEC]
    dataset = McapDataset.create(components=components, name="perception")
    # The test recording holds no decodable video.
    sequence_sample_id = add_mcaps.index_recording(
        dataset=dataset,
        mcap_path=str(helpers.write_mcap(tmp_path / "recording.mcap")),
        sync_component=VIDEO_COMPONENT,
        components=components,
    )
    session = db_manager.persistent_session()

    embed_mcap_sequences.embed_mcap_sequences(
        session=session,
        collection_id=dataset.collection_id,
        sequence_sample_ids=[sequence_sample_id],
    )

    model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=session, collection_id=dataset.collection_id
    )
    assert model_id is not None
    rows = sample_embedding_resolver.get_by_sample_ids(
        session=session, sample_ids=[sequence_sample_id], embedding_model_id=model_id
    )
    assert rows == []


def test_embed_mcap_sequences__invalid_frames_per_sequence(mocker: MockerFixture) -> None:
    with pytest.raises(ValueError, match="frames_per_sequence must be greater than 0"):
        embed_mcap_sequences.embed_mcap_sequences(
            session=mocker.MagicMock(),
            collection_id=uuid4(),
            sequence_sample_ids=[uuid4()],
            frames_per_sequence=0,
        )


def test_sample_keyframes() -> None:
    # The input is not ordered by log time.
    keyframes = [
        McapSequenceKeyframe(channel_id=1, log_time_ns=log_time_ns)
        for log_time_ns in (900, 0, 100, 200, 300, 400, 500, 600, 700, 800)
    ]

    chosen = embed_mcap_sequences.sample_keyframes(keyframes=keyframes, count=3)

    # The 10 keyframes split into 3 runs of length 10/3. The middles are at the indices
    # int(0.5 * 10/3) = 1, int(1.5 * 10/3) = 5 and int(2.5 * 10/3) = 8.
    assert [keyframe.log_time_ns for keyframe in chosen] == [100, 500, 800]


def test_sample_keyframes__one() -> None:
    keyframes = [
        McapSequenceKeyframe(channel_id=1, log_time_ns=log_time_ns)
        for log_time_ns in (100, 200, 300, 400, 500)
    ]

    chosen = embed_mcap_sequences.sample_keyframes(keyframes=keyframes, count=1)

    assert [keyframe.log_time_ns for keyframe in chosen] == [300]


def test_sample_keyframes__fewer_than_count() -> None:
    keyframes = [
        McapSequenceKeyframe(channel_id=1, log_time_ns=200),
        McapSequenceKeyframe(channel_id=1, log_time_ns=100),
    ]

    chosen = embed_mcap_sequences.sample_keyframes(keyframes=keyframes, count=8)

    assert [keyframe.log_time_ns for keyframe in chosen] == [100, 200]
