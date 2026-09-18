"""Get all MCAP sequences for a collection."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.database import db_array
from lightly_studio.models.group import SampleGroupLinkTable
from lightly_studio.models.mcap import McapTable
from lightly_studio.models.mcap_group_sequence import (
    McapGroupSequenceTable,
    McapSequenceFrame,
    McapSequenceView,
    McapSequenceViewsWithCount,
)
from lightly_studio.models.recording import RecordingTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sequence import SampleSequenceLinkTable


def get_all_by_collection_id(
    session: Session,
    collection_id: UUID,
    pagination: Paginated | None,
) -> McapSequenceViewsWithCount:
    """Retrieve MCAP sequences for a collection ordered by creation time.

    Only sequences that have a corresponding ``McapGroupSequenceTable`` row are
    returned. Results are ordered by ascending ``created_at`` of the underlying sample.

    Args:
        session: Database session for executing queries.
        collection_id: The ID of the collection to scope results to.
        pagination: Optional pagination parameters (offset and limit).

    Returns:
        McapSequenceViewsWithCount containing the page of sequences, the total
        count before pagination, and a cursor for the next page.
    """
    samples_query = (
        select(McapGroupSequenceTable)
        .join(SampleTable, col(McapGroupSequenceTable.sample_id) == col(SampleTable.sample_id))
        .where(col(SampleTable.collection_id) == collection_id)
        .order_by(col(SampleTable.created_at).asc(), col(SampleTable.sample_id).asc())
    )

    total_count_query = (
        select(func.count())
        .select_from(McapGroupSequenceTable)
        .join(SampleTable, col(McapGroupSequenceTable.sample_id) == col(SampleTable.sample_id))
        .where(col(SampleTable.collection_id) == collection_id)
    )

    if pagination is not None:
        samples_query = samples_query.offset(pagination.offset).limit(pagination.limit)

    total_count = session.exec(total_count_query).one()
    sequences = session.exec(samples_query).all()

    sequence_sample_ids = [seq.sample_id for seq in sequences]

    if not sequence_sample_ids:
        return McapSequenceViewsWithCount(
            samples=[],
            total_count=total_count,
            next_cursor=None,
        )

    sequence_sample_counts = _get_sequence_sample_counts(
        session=session,
        sequence_sample_ids=sequence_sample_ids,
    )
    sequence_frames = _get_sequence_frames(session=session, sequences=sequences)

    views = [
        McapSequenceView(
            sample_id=seq.sample_id,
            sample_count=sequence_sample_counts.get(seq.sample_id, 0),
            sequence_frame=sequence_frames.get(seq.sample_id),
        )
        for seq in sequences
    ]

    return McapSequenceViewsWithCount(
        samples=views,
        total_count=total_count,
        next_cursor=_compute_next_cursor(pagination=pagination, total_count=total_count),
    )


def _get_sequence_sample_counts(
    session: Session,
    sequence_sample_ids: Sequence[UUID],
) -> dict[UUID, int]:
    """Get the count of frames for each sequence.

    Args:
        session: Database session for executing queries.
        sequence_sample_ids: Non-empty sequence of sequence sample IDs.

    Returns:
        Dictionary mapping sequence sample_id to its frame count.
    """
    count_query = (
        select(
            SampleSequenceLinkTable.sequence_sample_id,
            func.count(col(SampleSequenceLinkTable.sample_id)).label("sample_count"),
        )
        .where(
            db_array.in_array(
                column=col(SampleSequenceLinkTable.sequence_sample_id),
                values=sequence_sample_ids,
            )
        )
        .group_by(col(SampleSequenceLinkTable.sequence_sample_id))
    )

    results = session.exec(count_query).all()
    return dict(results)


def _get_sequence_frames(
    session: Session,
    sequences: Sequence[McapGroupSequenceTable],
) -> dict[UUID, McapSequenceFrame]:
    """Get the first camera keyframe locator for each sequence.

    Only frames where ``keyframe_log_time_ns == log_time_ns`` are considered —
    these are self-contained keyframes decodable by the /camera-frame endpoint
    without any preceding reference frame. When a sequence has no such frames,
    it is absent from the returned dict. The first frame is chosen by ascending
    ``log_time_ns`` with ``channel_id`` as tie-breaker.

    Args:
        session: Database session for executing queries.
        sequences: Non-empty sequence of McapGroupSequenceTable rows.

    Returns:
        Dictionary mapping sequence sample_id to its first-keyframe locator.
    """
    recording_id_by_sample_id = {
        sequence.sample_id: sequence.recording_id for sequence in sequences
    }
    sequence_sample_ids = list(recording_id_by_sample_id)
    dataset_id_by_recording_id = _get_dataset_ids_by_recording_id(
        session=session,
        recording_ids=list(set(recording_id_by_sample_id.values())),
    )
    keyframe_rows = _get_sequence_keyframe_rows(
        session=session,
        sequence_sample_ids=sequence_sample_ids,
    )
    return _create_sequence_frames(
        keyframe_rows=keyframe_rows,
        recording_id_by_sample_id=recording_id_by_sample_id,
        dataset_id_by_recording_id=dataset_id_by_recording_id,
    )


def _get_dataset_ids_by_recording_id(
    session: Session,
    recording_ids: Sequence[UUID],
) -> dict[UUID, UUID]:
    """Get the dataset ID for each recording ID."""
    query = select(RecordingTable.recording_id, RecordingTable.dataset_id).where(
        col(RecordingTable.recording_id).in_(recording_ids)
    )
    return dict(session.exec(query).all())


def _get_sequence_keyframe_rows(
    session: Session,
    sequence_sample_ids: Sequence[UUID],
) -> Sequence[tuple[UUID, int, int]]:
    """Get every independently decodable MCAP frame in the requested sequences."""
    query = (
        select(
            SampleSequenceLinkTable.sequence_sample_id,
            McapTable.channel_id,
            McapTable.log_time_ns,
        )
        .join(
            SampleGroupLinkTable,
            col(SampleGroupLinkTable.parent_sample_id) == col(SampleSequenceLinkTable.sample_id),
        )
        .join(McapTable, col(McapTable.sample_id) == col(SampleGroupLinkTable.sample_id))
        .where(
            db_array.in_array(
                column=col(SampleSequenceLinkTable.sequence_sample_id),
                values=sequence_sample_ids,
            )
        )
        .where(col(McapTable.keyframe_log_time_ns) == col(McapTable.log_time_ns))
        .order_by(
            col(SampleSequenceLinkTable.sequence_sample_id),
            col(McapTable.log_time_ns).asc(),
            col(McapTable.channel_id).asc(),
        )
    )
    return session.exec(query).all()


def _create_sequence_frames(
    keyframe_rows: Sequence[tuple[UUID, int, int]],
    recording_id_by_sample_id: dict[UUID, UUID],
    dataset_id_by_recording_id: dict[UUID, UUID],
) -> dict[UUID, McapSequenceFrame]:
    """Create first-keyframe locators from ordered MCAP rows."""
    result: dict[UUID, McapSequenceFrame] = {}
    for sequence_sample_id, channel_id, log_time_ns in keyframe_rows:
        if sequence_sample_id not in result:
            recording_id = recording_id_by_sample_id[sequence_sample_id]
            result[sequence_sample_id] = McapSequenceFrame(
                dataset_id=dataset_id_by_recording_id[recording_id],
                recording_id=recording_id,
                channel_id=channel_id,
                keyframe_log_time_ns=str(log_time_ns),
            )
    return result


def _compute_next_cursor(
    pagination: Paginated | None,
    total_count: int,
) -> int | None:
    """Compute the next cursor for offset-based pagination."""
    if pagination and pagination.offset + pagination.limit < total_count:
        return pagination.offset + pagination.limit
    return None
