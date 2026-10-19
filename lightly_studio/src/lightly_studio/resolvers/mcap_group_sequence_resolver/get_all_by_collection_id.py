"""Get all MCAP sequences for a collection."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement
from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.database import db_array
from lightly_studio.models.group import SampleGroupLinkTable
from lightly_studio.models.mcap import McapTable
from lightly_studio.models.mcap_group_component_definition import (
    McapGroupComponentDefinitionTable,
)
from lightly_studio.models.mcap_group_sequence import (
    McapGroupSequenceTable,
    McapSequenceFrame,
    McapSequenceView,
    McapSequenceViewsWithCount,
)
from lightly_studio.models.recording import RecordingTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import mcap_group_sequence_resolver, similarity_utils
from lightly_studio.resolvers.mcap_group_sequence_resolver.mcap_sequence_filter import (
    McapSequenceFilter,
)
from lightly_studio.type_definitions import QueryType


def get_all_by_collection_id(
    session: Session,
    collection_id: UUID,
    pagination: Paginated | None,
    filters: McapSequenceFilter | None = None,
    text_embedding: list[float] | None = None,
) -> McapSequenceViewsWithCount:
    """Retrieve MCAP sequences for a collection ordered by creation time.

    Only sequences that have a corresponding ``McapGroupSequenceTable`` row are
    returned. Results are ordered by ascending ``created_at`` of the underlying sample.
    When ``text_embedding`` is given and the collection has a default embedding model,
    only sequences with an embedding are returned, ordered by similarity.

    Args:
        session: Database session for executing queries.
        collection_id: The ID of the collection to scope results to.
        pagination: Optional pagination parameters (offset and limit).
        filters: Optional filters for the sequences.
        text_embedding: Optional embedding to order the sequences by similarity to.

    Returns:
        McapSequenceViewsWithCount containing the page of sequences, the total
        count before pagination, and a cursor for the next page.
    """
    embedding_model_id, distance_expr = similarity_utils.get_distance_expression(
        session=session,
        collection_id=collection_id,
        text_embedding=text_embedding,
    )

    total_count_query = _scope_query(
        query=select(func.count()).select_from(McapGroupSequenceTable),
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
        filters=filters,
    )
    total_count = session.exec(total_count_query).one()

    sequences: list[McapGroupSequenceTable]
    similarity_scores: dict[UUID, float] = {}
    if distance_expr is not None:
        similarity_query = _scope_query(
            query=select(McapGroupSequenceTable, distance_expr),
            collection_id=collection_id,
            embedding_model_id=embedding_model_id,
            filters=filters,
        ).order_by(distance_expr, *_default_order())
        similarity_query = _paginate(query=similarity_query, pagination=pagination)
        rows = session.exec(similarity_query).all()
        sequences = [sequence for sequence, _ in rows]
        similarity_scores = {
            sequence.sample_id: similarity_utils.distance_to_similarity(distance)
            for sequence, distance in rows
        }
    else:
        samples_query = _scope_query(
            query=select(McapGroupSequenceTable),
            collection_id=collection_id,
            embedding_model_id=None,
            filters=filters,
        ).order_by(*_default_order())
        samples_query = _paginate(query=samples_query, pagination=pagination)
        sequences = list(session.exec(samples_query).all())

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
    sequence_frames = _get_sequence_frames(
        session=session,
        sequences=sequences,
        collection_id=collection_id,
    )

    file_name_by_recording_id = _get_file_names_by_recording_id(
        session=session,
        recording_ids=list({seq.recording_id for seq in sequences}),
    )

    views = [
        McapSequenceView(
            sample_id=seq.sample_id,
            recording_id=seq.recording_id,
            file_name=file_name_by_recording_id[seq.recording_id],
            sample_count=sequence_sample_counts.get(seq.sample_id, 0),
            sequence_frame=sequence_frames.get(seq.sample_id),
            similarity_score=similarity_scores.get(seq.sample_id),
        )
        for seq in sequences
    ]

    return McapSequenceViewsWithCount(
        samples=views,
        total_count=total_count,
        next_cursor=_compute_next_cursor(pagination=pagination, total_count=total_count),
    )


def _scope_query(
    query: QueryType,
    collection_id: UUID,
    embedding_model_id: UUID | None,
    filters: McapSequenceFilter | None,
) -> QueryType:
    """Scope a query on McapGroupSequenceTable to a collection, embeddings and filters.

    With an embedding model, only sequences with an embedding of that model are kept.
    """
    query = query.join(
        SampleTable, col(McapGroupSequenceTable.sample_id) == col(SampleTable.sample_id)
    ).where(col(SampleTable.collection_id) == collection_id)
    query = similarity_utils.apply_similarity_join(
        query=query,
        sample_id_column=col(McapGroupSequenceTable.sample_id),
        embedding_model_id=embedding_model_id,
    )
    if filters is not None:
        query = filters.apply(query)
    return query


def _default_order() -> list[ColumnElement[Any]]:
    """Order by creation time, with the sample ID as tiebreaker for a stable order."""
    return [col(SampleTable.created_at).asc(), col(SampleTable.sample_id).asc()]


def _paginate(query: QueryType, pagination: Paginated | None) -> QueryType:
    if pagination is None:
        return query
    return query.offset(pagination.offset).limit(pagination.limit)


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
    collection_id: UUID,
) -> dict[UUID, McapSequenceFrame]:
    """Get the first camera keyframe locator for each sequence.

    Only frames where ``keyframe_log_time_ns == log_time_ns`` are considered —
    these are self-contained keyframes decodable by the /camera-frame endpoint
    without any preceding reference frame. The camera slot is resolved once for
    the whole collection (lowest ``group_component_index`` VIDEO_FRAME slot);
    sequences whose resolved slot has no such frame are absent from the dict.

    Args:
        session: Database session for executing queries.
        sequences: Non-empty sequence of McapGroupSequenceTable rows.
        collection_id: The SEQUENCE collection ID, used to resolve the camera slot.

    Returns:
        Dictionary mapping sequence sample_id to its first-keyframe locator.
    """
    video_frame_collection_id = mcap_group_sequence_resolver.get_first_video_frame_collection_id(
        session=session,
        sequence_collection_id=collection_id,
    )
    if video_frame_collection_id is None:
        return {}
    recording_id_by_sample_id = {
        sequence.sample_id: sequence.recording_id for sequence in sequences
    }
    sequence_sample_ids = list(recording_id_by_sample_id)
    dataset_id_by_recording_id = _get_dataset_ids_by_recording_id(
        session=session,
        recording_ids=list(set(recording_id_by_sample_id.values())),
    )
    keyframe_rows = _get_first_keyframe_per_sequence(
        session=session,
        sequence_sample_ids=sequence_sample_ids,
        collection_id=video_frame_collection_id,
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


def _get_file_names_by_recording_id(
    session: Session,
    recording_ids: Sequence[UUID],
) -> dict[UUID, str]:
    """Get the file name, the last segment of the URI, for each recording ID."""
    query = select(RecordingTable.recording_id, RecordingTable.uri).where(
        col(RecordingTable.recording_id).in_(recording_ids)
    )
    return {
        recording_id: uri.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
        for recording_id, uri in session.exec(query).all()
    }


def _get_first_keyframe_per_sequence(
    session: Session,
    sequence_sample_ids: Sequence[UUID],
    collection_id: UUID,
) -> Sequence[tuple[UUID, int, int]]:
    """Get the first independently decodable MCAP keyframe for each sequence.

    A ``ROW_NUMBER`` window function partitioned by ``sequence_sample_id`` and
    ordered by ``log_time_ns ASC`` selects the first keyframe per sequence in SQL,
    avoiding full materialisation of all keyframe rows. Only frames belonging to the
    component slot identified by ``collection_id`` are considered.

    Args:
        session: Database session for executing queries.
        sequence_sample_ids: Non-empty sequence of sequence sample IDs.
        collection_id: The component-slot collection_id to filter frames by.

    Returns:
        One ``(sequence_sample_id, channel_id, log_time_ns)`` tuple per sequence
        that has at least one independently decodable keyframe in ``collection_id``.
    """
    ranked = (
        select(
            SampleSequenceLinkTable.sequence_sample_id,
            McapTable.channel_id,
            McapTable.log_time_ns,
            func.row_number()
            .over(
                partition_by=col(SampleSequenceLinkTable.sequence_sample_id),
                order_by=col(McapTable.log_time_ns).asc(),
            )
            .label("rn"),
        )
        .join(
            SampleGroupLinkTable,
            col(SampleGroupLinkTable.parent_sample_id) == col(SampleSequenceLinkTable.sample_id),
        )
        .join(McapTable, col(McapTable.sample_id) == col(SampleGroupLinkTable.sample_id))
        .join(SampleTable, col(SampleTable.sample_id) == col(McapTable.sample_id))
        .join(
            McapGroupComponentDefinitionTable,
            col(McapGroupComponentDefinitionTable.collection_id) == col(SampleTable.collection_id),
        )
        .where(
            db_array.in_array(
                column=col(SampleSequenceLinkTable.sequence_sample_id),
                values=sequence_sample_ids,
            )
        )
        .where(col(McapGroupComponentDefinitionTable.collection_id) == collection_id)
        .where(col(McapTable.keyframe_log_time_ns) == col(McapTable.log_time_ns))
    ).subquery()

    query = select(
        ranked.c.sequence_sample_id,
        ranked.c.channel_id,
        ranked.c.log_time_ns,
    ).where(ranked.c.rn == 1)

    return session.exec(query).all()


def _create_sequence_frames(
    keyframe_rows: Sequence[tuple[UUID, int, int]],
    recording_id_by_sample_id: dict[UUID, UUID],
    dataset_id_by_recording_id: dict[UUID, UUID],
) -> dict[UUID, McapSequenceFrame]:
    """Create first-keyframe locators from one-per-sequence MCAP rows."""
    return {
        sequence_sample_id: McapSequenceFrame(
            dataset_id=dataset_id_by_recording_id[recording_id_by_sample_id[sequence_sample_id]],
            recording_id=recording_id_by_sample_id[sequence_sample_id],
            channel_id=channel_id,
            keyframe_log_time_ns=str(log_time_ns),
        )
        for sequence_sample_id, channel_id, log_time_ns in keyframe_rows
    }


def _compute_next_cursor(
    pagination: Paginated | None,
    total_count: int,
) -> int | None:
    """Compute the next cursor for offset-based pagination."""
    if pagination and pagination.offset + pagination.limit < total_count:
        return pagination.offset + pagination.limit
    return None
