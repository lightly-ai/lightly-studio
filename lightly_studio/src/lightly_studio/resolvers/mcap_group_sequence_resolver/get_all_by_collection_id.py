"""Get all MCAP sequences for a collection."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.database import db_array
from lightly_studio.models.mcap_group_sequence import (
    McapGroupSequenceTable,
    McapSequenceView,
    McapSequenceViewsWithCount,
)
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
        .order_by(col(SampleTable.created_at).asc())
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

    views = [
        McapSequenceView(
            sample_id=seq.sample_id,
            sample_count=sequence_sample_counts.get(seq.sample_id, 0),
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


def _compute_next_cursor(
    pagination: Paginated | None,
    total_count: int,
) -> int | None:
    """Compute the next cursor for offset-based pagination."""
    if pagination and pagination.offset + pagination.limit < total_count:
        return pagination.offset + pagination.limit
    return None
