"""Tests for get_all_by_collection_id in mcap_group_sequence_resolver."""

from uuid import UUID

from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.collection import SampleType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.models.sample import SampleCreate
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import (
    mcap_group_sequence_resolver,
    recording_resolver,
    sample_resolver,
)
from tests.helpers_resolvers import create_collection


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
    """Cursor pagination returns the correct page and next_cursor."""
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)

    recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=seq_col.dataset_id,
        uri="/bags/drive_001.mcap",
        format_=RecordingFormat.MCAP,
    )

    mcap_group_sequence_resolver.create(
        session=db_session,
        collection_id=seq_col.collection_id,
        recording_id=recording_id,
    )
    mcap_group_sequence_resolver.create(
        session=db_session,
        collection_id=seq_col.collection_id,
        recording_id=recording_id,
    )
    mcap_group_sequence_resolver.create(
        session=db_session,
        collection_id=seq_col.collection_id,
        recording_id=recording_id,
    )

    page_1 = mcap_group_sequence_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=seq_col.collection_id,
        pagination=Paginated(offset=0, limit=2),
    )

    assert page_1.total_count == 3
    assert len(page_1.samples) == 2
    assert page_1.next_cursor == 2

    page_2 = mcap_group_sequence_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=seq_col.collection_id,
        pagination=Paginated(offset=2, limit=2),
    )

    assert page_2.total_count == 3
    assert len(page_2.samples) == 1
    assert page_2.next_cursor is None


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
