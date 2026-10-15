"""Builds an MCAP sequence tick with a decodable camera and a lidar channel."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import group_resolver
from tests import helpers_resolvers
from tests.core.mcap import helpers as mcap_helpers
from tests.resolvers.mcap_group_sequence_resolver import helpers

# The video is one GOP: a black keyframe at 1.0 s, then gray, white and black frames.
VIDEO_GRAY_LEVELS = (0, 128, 255, 0)
KEYFRAME_NS = 1_000_000_000
CAMERA_LOG_TIME_NS = 1_100_000_000
LIDAR_LOG_TIME_NS = 1_050_000_000


@dataclass(frozen=True)
class TickFixture:
    dataset_id: UUID
    sequence_id: UUID
    camera_channel_id: int
    lidar_channel_id: int


def create_tick(session: Session, tmp_path: Path) -> TickFixture:
    """Creates a sequence whose tick 0 has the camera frame at 1.1 s and the lidar at 1.05 s."""
    mcap_path = mcap_helpers.write_mcap(
        path=tmp_path / "recording.mcap",
        video_access_units=mcap_helpers.h264_access_units(gray_levels=VIDEO_GRAY_LEVELS),
    )
    with McapFileReader(mcap_path) as reader:
        channel_ids = {topic.name: topic.channel_id for topic in reader.get_topics()}
    fixture = helpers.create_mcap_sequence(session=session, uri=str(mcap_path))
    camera = helpers_resolvers.create_mcap(
        session=session,
        collection_id=fixture.slots["front"].collection_id,
        channel_id=channel_ids[mcap_helpers.CAMERA_VIDEO_TOPIC],
        log_time_ns=CAMERA_LOG_TIME_NS,
        keyframe_log_time_ns=KEYFRAME_NS,
    )
    lidar = helpers_resolvers.create_mcap(
        session=session,
        collection_id=fixture.slots["pcl_front"].collection_id,
        channel_id=channel_ids[mcap_helpers.LIDAR_POINTS_TOPIC],
        log_time_ns=LIDAR_LOG_TIME_NS,
        keyframe_log_time_ns=None,
    )
    group_ids = group_resolver.create_many(
        session=session,
        collection_id=fixture.group_collection.collection_id,
        groups=[{camera.sample_id, lidar.sample_id}],
    )
    session.add(
        SampleSequenceLinkTable(
            sample_id=group_ids[0],
            sequence_sample_id=fixture.sample_id,
            seq_number=0,
            timestamp_ns=LIDAR_LOG_TIME_NS,
        )
    )
    session.commit()
    return TickFixture(
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
        camera_channel_id=channel_ids[mcap_helpers.CAMERA_VIDEO_TOPIC],
        lidar_channel_id=channel_ids[mcap_helpers.LIDAR_POINTS_TOPIC],
    )
