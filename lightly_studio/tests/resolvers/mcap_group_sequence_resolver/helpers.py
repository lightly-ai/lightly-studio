"""Helpers for MCAP group sequence resolver tests."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.mcap import McapCreate
from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.models.sequence import SampleSequenceLinkCreate
from lightly_studio.resolvers import (
    collection_resolver,
    group_resolver,
    mcap_group_component_definition_resolver,
    mcap_group_sequence_resolver,
    mcap_resolver,
    recording_resolver,
    sequence_resolver,
)
from tests.helpers_resolvers import create_collection


@dataclass(frozen=True)
class McapSequenceFixture:
    """A full MCAP sequence: its schema (GROUP + slots) and its bag (recording)."""

    sequence_collection: CollectionTable
    sample_id: UUID
    group_collection: CollectionTable
    slots: dict[str, CollectionTable]
    recording_id: UUID


def create_mcap_sequence(
    session: Session,
    uri: str = "/data/perception.mcap",
    extra_slots: list[tuple[str, SampleType]] | None = None,
) -> McapSequenceFixture:
    """Creates a SEQUENCE collection with a GROUP child of two MCAP slots and a bag.

    The slots are "front" (video_frame, channel_id=3, frame_id="main") at index 0 and
    "pcl_front" (point_cloud, channel_id=7, frame_id="livox_front_left") at index 1.

    Args:
        session: The database session.
        uri: The bag path to record on the recording.
        extra_slots: Additional, non-MCAP, group components to create alongside the
            two MCAP slots, e.g. `[("thumbnail", SampleType.IMAGE)]`.
    """
    sequence_collection = create_collection(session=session, sample_type=SampleType.SEQUENCE)
    group_collection = create_collection(
        session=session,
        sample_type=SampleType.GROUP,
        parent_collection_id=sequence_collection.collection_id,
    )
    components = [("front", SampleType.MCAP), ("pcl_front", SampleType.MCAP)]
    components.extend(extra_slots or [])
    slots = collection_resolver.create_group_components(
        session=session,
        parent_collection_id=group_collection.collection_id,
        components=components,
    )
    mcap_group_component_definition_resolver.create(
        session=session,
        collection_id=slots["front"].collection_id,
        mcap_data_type=McapDataType.VIDEO_FRAME,
        channel_id=3,
        frame_id="main",
    )
    mcap_group_component_definition_resolver.create(
        session=session,
        collection_id=slots["pcl_front"].collection_id,
        mcap_data_type=McapDataType.POINT_CLOUD,
        channel_id=7,
        frame_id="livox_front_left",
    )

    recording_id = recording_resolver.create(
        session=session,
        dataset_id=sequence_collection.dataset_id,
        uri=uri,
        format_=RecordingFormat.MCAP,
    )
    sample_id = mcap_group_sequence_resolver.create(
        session=session,
        collection_id=sequence_collection.collection_id,
        recording_id=recording_id,
    )

    return McapSequenceFixture(
        sequence_collection=sequence_collection,
        sample_id=sample_id,
        group_collection=group_collection,
        slots=slots,
        recording_id=recording_id,
    )


def add_mcap_ticks_to_sequence(
    session: Session,
    fixture: McapSequenceFixture,
    ticks: list[tuple[int, int | None]],
) -> None:
    group_ids = [
        create_mcap_tick(
            session=session,
            fixture=fixture,
            camera_log_time_ns=camera_log_time_ns,
            camera_keyframe_log_time_ns=camera_keyframe_log_time_ns,
        )
        for camera_log_time_ns, camera_keyframe_log_time_ns in ticks
    ]
    sequence_resolver.add_samples(
        session=session,
        sequence_sample_id=fixture.sample_id,
        links=[
            SampleSequenceLinkCreate(
                sample_id=group_id,
                seq_number=sequence_number,
                timestamp_ns=ticks[sequence_number][0],
            )
            for sequence_number, group_id in enumerate(group_ids)
        ],
    )


def create_mcap_tick(
    session: Session,
    fixture: McapSequenceFixture,
    camera_log_time_ns: int,
    camera_keyframe_log_time_ns: int | None,
) -> UUID:
    camera_sample_id = create_mcap_sample(
        session=session,
        collection_id=fixture.slots["front"].collection_id,
        channel_id=3,
        log_time_ns=camera_log_time_ns,
        keyframe_log_time_ns=camera_keyframe_log_time_ns,
    )
    point_cloud_sample_id = create_mcap_sample(
        session=session,
        collection_id=fixture.slots["pcl_front"].collection_id,
        channel_id=7,
        log_time_ns=camera_log_time_ns + 1,
        keyframe_log_time_ns=None,
    )
    return group_resolver.create_many(
        session=session,
        collection_id=fixture.group_collection.collection_id,
        groups=[{camera_sample_id, point_cloud_sample_id}],
    )[0]


def create_mcap_sample(
    session: Session,
    collection_id: UUID,
    channel_id: int,
    log_time_ns: int,
    keyframe_log_time_ns: int | None,
) -> UUID:
    return mcap_resolver.create_many(
        session=session,
        collection_id=collection_id,
        samples=[
            McapCreate(
                channel_id=channel_id,
                log_time_ns=log_time_ns,
                capture_timestamp_ns=log_time_ns,
                keyframe_log_time_ns=keyframe_log_time_ns,
            )
        ],
    )[0]
