"""Keyset (seek) implementation of annotation adjacency — the fast path.

An annotation sorts by its parent media's ``file_path_abs``. The window path reaches that
through a ``coalesce`` over two outer-joined tables, which no index can drive an ordered
scan over. Every annotation in a collection shares one parent kind, so resolving that kind
up front lets us inner-join a single parent table and seek on a plain indexed column.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.collection import SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers.adjacents import keyset_seek
from lightly_studio.resolvers.annotations import annotation_ordering
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter


def get_adjacent_annotations_keyset(
    session: Session,
    sample_id: UUID,
    filters: AnnotationsFilter,
    parent_sample_type: SampleType,
) -> AdjacentResultView | None:
    """Find the previous/next annotation and the anchor's position via keyset seeks.

    Args:
        session: Database session.
        sample_id: The anchor annotation whose neighbours we want.
        filters: Annotation filters constraining the set; must scope the collection.
        parent_sample_type: Sample type of the annotations' parent samples.

    Returns:
        The adjacency result, or ``None`` if the anchor is not in the filtered set.
    """
    sort_keys = annotation_ordering.build_sort_keys(
        file_path_abs=annotation_ordering.file_path_abs_expression(sample_type=parent_sample_type),
        created_at=col(AnnotationBaseTable.created_at),
        annotation_sample_id=col(AnnotationBaseTable.sample_id),
    )

    anchor = keyset_seek.fetch_anchor(
        session=session,
        query=_filtered_query(
            columns=[column for column, _ in sort_keys],
            filters=filters,
            parent_sample_type=parent_sample_type,
        ).where(col(AnnotationBaseTable.sample_id) == sample_id),
    )
    if anchor is None:
        # The annotation is not part of the filtered set.
        return None

    return keyset_seek.get_adjacent_result(
        session=session,
        sample_id=sample_id,
        base_query=_filtered_query(
            columns=[col(AnnotationBaseTable.sample_id)],
            filters=filters,
            parent_sample_type=parent_sample_type,
        ),
        sort_keys=sort_keys,
        anchor=anchor,
    )


def _filtered_query(
    columns: Sequence[keyset_seek.SortColumn],
    filters: AnnotationsFilter,
    parent_sample_type: SampleType,
) -> Any:
    """Select the given columns from the filtered annotations, joined to their parents.

    Type is loosened to Any because the callers select different row shapes: sample ids for
    the seeks and counts, the sort-key tuple for the anchor.
    """
    query = select(*columns).select_from(AnnotationBaseTable)
    return filters.apply(_join_parent_media(query=query, parent_sample_type=parent_sample_type))


def _join_parent_media(query: Any, parent_sample_type: SampleType) -> Any:
    """Inner-join the one parent table the annotations' sort key lives on.

    Raises:
        NotImplementedError: If the sample type has no parent file path.
    """
    if parent_sample_type == SampleType.IMAGE:
        return query.join(
            ImageTable,
            col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )

    if parent_sample_type == SampleType.VIDEO_FRAME:
        return query.join(
            VideoFrameTable,
            col(VideoFrameTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        ).join(
            VideoTable,
            col(VideoTable.sample_id) == col(VideoFrameTable.parent_sample_id),
        )

    raise NotImplementedError(f"Unsupported parent sample type: {parent_sample_type}")
