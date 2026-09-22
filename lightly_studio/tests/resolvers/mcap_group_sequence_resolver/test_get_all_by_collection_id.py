"""Tests for get_all_by_collection_id in mcap_group_sequence_resolver."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import Session, insert

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.collection import SampleType
from lightly_studio.models.mcap import McapCreate
from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.models.mcap_group_sequence import McapGroupSequenceTable
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.models.sample import SampleCreate, SampleTable
from lightly_studio.models.sequence import (
    SampleSequenceLinkCreate,
    SampleSequenceLinkTable,
    SequenceTable,
)
from lightly_studio.resolvers import (
    collection_resolver,
    group_resolver,
    mcap_group_component_definition_resolver,
    mcap_group_sequence_resolver,
    mcap_resolver,
    recording_resolver,
    sample_resolver,
    sequence_resolver,
)
from tests.helpers_resolvers import create_collection
from tests.resolvers.mcap_group_sequence_resolver import helpers
from tests.resolvers.mcap_group_sequence_resolver.helpers import McapSequenceFixture


def test_get_all_by_collection_id__empty_collection(db_session: Session) -> None:
    """Returns empty result for a collection with no sequences."""
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)

    result = mcap_group_sequence_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=seq_col.collection_id,
        pagination=None,
    )

    assert result.total_count == 0
    assert result.samples == []
    assert result.next_cursor is None


def test_get_all_by_collection_id__returns_mcap_sequences(db_session: Session) -> None:
    """Returns sequences linked to MCAP recordings with correct frame counts."""
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    frame_col = create_collection(session=db_session, sample_type=SampleType.IMAGE)

    recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=seq_col.dataset_id,
        uri="/bags/drive_001.mcap",
        format_=RecordingFormat.MCAP,
    )

    frame_ids = sample_resolver.create_many(
        session=db_session,
        samples=[
            SampleCreate(collection_id=frame_col.collection_id),
            SampleCreate(collection_id=frame_col.collection_id),
        ],
    )

    seq_id = mcap_group_sequence_resolver.create(
        session=db_session,
        collection_id=seq_col.collection_id,
        recording_id=recording_id,
    )
    _link_frames_to_sequence(
        session=db_session,
        sequence_sample_id=seq_id,
        frame_sample_ids=frame_ids,
    )

    result = mcap_group_sequence_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=seq_col.collection_id,
        pagination=None,
    )

    assert result.total_count == 1
    assert len(result.samples) == 1
    assert result.samples[0].sample_id == seq_id
    assert result.samples[0].sample_count == 2
    assert result.samples[0].sequence_frame is None
    assert result.next_cursor is None


def test_get_all_by_collection_id__scoped_to_collection(db_session: Session) -> None:
    """Sequences from a different collection are not returned."""
    seq_col_a = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    seq_col_b = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)

    recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=seq_col_a.dataset_id,
        uri="/bags/drive_001.mcap",
        format_=RecordingFormat.MCAP,
    )

    mcap_group_sequence_resolver.create(
        session=db_session,
        collection_id=seq_col_a.collection_id,
        recording_id=recording_id,
    )

    result = mcap_group_sequence_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=seq_col_b.collection_id,
        pagination=None,
    )

    assert result.total_count == 0
    assert result.samples == []


def test_get_all_by_collection_id__pagination(db_session: Session) -> None:
    """Pagination with tied created_at timestamps is broken by sample_id ascending."""
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)

    recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=seq_col.dataset_id,
        uri="/bags/drive_001.mcap",
        format_=RecordingFormat.MCAP,
    )

    # Insert samples with the same created_at to force ties, using deterministic
    # UUIDs so the expected tie-break order (sample_id asc) is predictable.
    fixed_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
    seq_id_a = UUID("00000000-0000-0000-0000-000000000001")
    seq_id_b = UUID("00000000-0000-0000-0000-000000000002")
    seq_id_c = UUID("00000000-0000-0000-0000-000000000003")

    db_session.execute(
        insert(SampleTable).values(
            [
                {
                    "sample_id": seq_id_a,
                    "collection_id": seq_col.collection_id,
                    "created_at": fixed_time,
                    "updated_at": fixed_time,
                },
                {
                    "sample_id": seq_id_b,
                    "collection_id": seq_col.collection_id,
                    "created_at": fixed_time,
                    "updated_at": fixed_time,
                },
                {
                    "sample_id": seq_id_c,
                    "collection_id": seq_col.collection_id,
                    "created_at": fixed_time,
                    "updated_at": fixed_time,
                },
            ]
        )
    )
    db_session.bulk_save_objects(
        [
            SequenceTable(sample_id=seq_id_a),
            SequenceTable(sample_id=seq_id_b),
            SequenceTable(sample_id=seq_id_c),
        ]
    )
    db_session.bulk_save_objects(
        [
            McapGroupSequenceTable(sample_id=seq_id_a, recording_id=recording_id),
            McapGroupSequenceTable(sample_id=seq_id_b, recording_id=recording_id),
            McapGroupSequenceTable(sample_id=seq_id_c, recording_id=recording_id),
        ]
    )
    db_session.commit()

    page_1 = mcap_group_sequence_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=seq_col.collection_id,
        pagination=Paginated(offset=0, limit=2),
    )

    assert page_1.total_count == 3
    assert [s.sample_id for s in page_1.samples] == [seq_id_a, seq_id_b]
    assert page_1.next_cursor == 2

    page_2 = mcap_group_sequence_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=seq_col.collection_id,
        pagination=Paginated(offset=2, limit=2),
    )

    assert page_2.total_count == 3
    assert [s.sample_id for s in page_2.samples] == [seq_id_c]
    assert page_2.next_cursor is None


def test_get_all_by_collection_id__returns_sequence_frame(db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session, uri="/bags/drive_001.mcap")
    _add_mcap_ticks_to_sequence(
        session=db_session,
        fixture=fixture,
        ticks=[(100, 100), (200, 200)],
    )
    result = mcap_group_sequence_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=fixture.sequence_collection.collection_id,
        pagination=None,
    )
    sequence_frame = result.samples[0].sequence_frame

    assert sequence_frame is not None
    assert (
        sequence_frame.dataset_id,
        sequence_frame.recording_id,
        sequence_frame.channel_id,
        sequence_frame.keyframe_log_time_ns,
    ) == (fixture.sequence_collection.dataset_id, fixture.recording_id, 3, "100")


def test_get_all_by_collection_id__no_sequence_frame_without_camera_frames(
    db_session: Session,
) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session, uri="/bags/lidar_001.mcap")
    _add_mcap_ticks_to_sequence(
        session=db_session,
        fixture=fixture,
        ticks=[(100, 50)],
    )
    result = mcap_group_sequence_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=fixture.sequence_collection.collection_id,
        pagination=None,
    )

    assert len(result.samples) == 1
    assert result.samples[0].sequence_frame is None


def test_get_all_by_collection_id__sequence_frame_uses_lowest_index_slot_when_channel_changes(
    db_session: Session,
) -> None:
    """Uses the lowest-indexed VIDEO_FRAME slot instead of its stored channel ID."""
    sequence_collection = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    group_collection = create_collection(
        session=db_session,
        sample_type=SampleType.GROUP,
        parent_collection_id=sequence_collection.collection_id,
    )
    slots = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_collection.collection_id,
        components=[("front", SampleType.MCAP), ("rear", SampleType.MCAP)],
    )
    mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=slots["front"].collection_id,
        mcap_data_type=McapDataType.VIDEO_FRAME,
        channel_id=3,
        frame_id="front",
    )
    mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=slots["rear"].collection_id,
        mcap_data_type=McapDataType.VIDEO_FRAME,
        channel_id=5,
        frame_id="rear",
    )
    recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=sequence_collection.dataset_id,
        uri="/bags/two_cameras.mcap",
        format_=RecordingFormat.MCAP,
    )
    sample_id = mcap_group_sequence_resolver.create(
        session=db_session,
        collection_id=sequence_collection.collection_id,
        recording_id=recording_id,
    )
    # The front slot's channel ID is from an earlier bag. This recording uses channel 8.
    # Rear has an earlier keyframe, but front has the lower group component index.
    rear_sample_id = _create_mcap_sample(
        session=db_session,
        collection_id=slots["rear"].collection_id,
        channel_id=5,
        log_time_ns=100,
        keyframe_log_time_ns=100,
    )
    front_sample_id = _create_mcap_sample(
        session=db_session,
        collection_id=slots["front"].collection_id,
        channel_id=8,
        log_time_ns=200,
        keyframe_log_time_ns=200,
    )
    group_id = group_resolver.create_many(
        session=db_session,
        collection_id=group_collection.collection_id,
        groups=[{front_sample_id, rear_sample_id}],
    )[0]
    sequence_resolver.add_samples(
        session=db_session,
        sequence_sample_id=sample_id,
        links=[SampleSequenceLinkCreate(sample_id=group_id, seq_number=0, timestamp_ns=100)],
    )

    result = mcap_group_sequence_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=sequence_collection.collection_id,
        pagination=None,
    )
    sequence_frame = result.samples[0].sequence_frame

    assert sequence_frame is not None
    assert sequence_frame.channel_id == 8
    assert sequence_frame.keyframe_log_time_ns == "200"


def test_get_all_by_collection_id__no_sequence_frame_when_resolved_channel_has_no_keyframe(
    db_session: Session,
) -> None:
    """sequence_frame is None when the resolved camera has no keyframe, even if another does."""
    sequence_collection = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    group_collection = create_collection(
        session=db_session,
        sample_type=SampleType.GROUP,
        parent_collection_id=sequence_collection.collection_id,
    )
    slots = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_collection.collection_id,
        components=[("front", SampleType.MCAP), ("rear", SampleType.MCAP)],
    )
    mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=slots["front"].collection_id,
        mcap_data_type=McapDataType.VIDEO_FRAME,
        channel_id=3,
        frame_id="front",
    )
    mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=slots["rear"].collection_id,
        mcap_data_type=McapDataType.VIDEO_FRAME,
        channel_id=5,
        frame_id="rear",
    )
    recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=sequence_collection.dataset_id,
        uri="/bags/two_cameras.mcap",
        format_=RecordingFormat.MCAP,
    )
    sample_id = mcap_group_sequence_resolver.create(
        session=db_session,
        collection_id=sequence_collection.collection_id,
        recording_id=recording_id,
    )
    # front (resolved camera) has no self-decodable keyframe; rear does.
    front_sample_id = _create_mcap_sample(
        session=db_session,
        collection_id=slots["front"].collection_id,
        channel_id=3,
        log_time_ns=100,
        keyframe_log_time_ns=50,  # Not a keyframe — keyframe_log_time_ns != log_time_ns.
    )
    rear_sample_id = _create_mcap_sample(
        session=db_session,
        collection_id=slots["rear"].collection_id,
        channel_id=5,
        log_time_ns=100,
        keyframe_log_time_ns=100,
    )
    group_id = group_resolver.create_many(
        session=db_session,
        collection_id=group_collection.collection_id,
        groups=[{front_sample_id, rear_sample_id}],
    )[0]
    sequence_resolver.add_samples(
        session=db_session,
        sequence_sample_id=sample_id,
        links=[SampleSequenceLinkCreate(sample_id=group_id, seq_number=0, timestamp_ns=100)],
    )

    result = mcap_group_sequence_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=sequence_collection.collection_id,
        pagination=None,
    )

    assert result.samples[0].sequence_frame is None


def _add_mcap_ticks_to_sequence(
    session: Session,
    fixture: McapSequenceFixture,
    ticks: list[tuple[int, int | None]],
) -> None:
    group_ids = [
        _create_mcap_tick(
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


def _create_mcap_tick(
    session: Session,
    fixture: McapSequenceFixture,
    camera_log_time_ns: int,
    camera_keyframe_log_time_ns: int | None,
) -> UUID:
    camera_sample_id = _create_mcap_sample(
        session=session,
        collection_id=fixture.slots["front"].collection_id,
        channel_id=3,
        log_time_ns=camera_log_time_ns,
        keyframe_log_time_ns=camera_keyframe_log_time_ns,
    )
    point_cloud_sample_id = _create_mcap_sample(
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


def _create_mcap_sample(
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


def _link_frames_to_sequence(
    session: Session,
    sequence_sample_id: UUID,
    frame_sample_ids: list[UUID],
) -> None:
    links = [
        SampleSequenceLinkTable(
            sample_id=fid,
            sequence_sample_id=sequence_sample_id,
            seq_number=i,
        )
        for i, fid in enumerate(frame_sample_ids)
    ]
    session.bulk_save_objects(objects=links)
    session.commit()
