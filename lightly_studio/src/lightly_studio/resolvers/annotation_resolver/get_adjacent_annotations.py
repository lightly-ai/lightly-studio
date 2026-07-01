"""Resolver for getting adjacent annotations for a given annotation ID."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

import sqlalchemy
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers.adjacents import keyset_seek
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter


def get_adjacent_annotations(
    session: Session,
    sample_id: UUID,
    filters: AnnotationsFilter,
) -> AdjacentResultView | None:
    """Get the previous and next annotation for a sample in the current sort order.

    Uses a keyset (seek) lookup instead of a full sort + window scan over the whole
    collection (LIG-9925). Annotations are ordered by the parent media file path,
    ``created_at``, then ``sample_id``; all three are non-nullable so the ordering —
    and therefore prev/next and the position count — is total and stable.
    """
    if not filters.collection_ids:
        raise ValueError("Collection IDs must be provided in filters.")

    sort_keys = _keyset_sort_keys()
    anchor = _fetch_anchor_values(
        session=session, sample_id=sample_id, filters=filters, sort_keys=sort_keys
    )
    if anchor is None:
        # The annotation is not part of the (filtered) set.
        return None

    return keyset_seek.get_adjacent_result(
        session=session,
        sample_id=sample_id,
        base_query=_keyset_sample_id_query(filters=filters),
        anchor=anchor,
        sort_keys=sort_keys,
    )


def _keyset_sort_keys() -> list[keyset_seek.SortKey]:
    """Build the ordered, fully deterministic keyset sort keys.

    Mirrors the previous window ordering: the parent media ``file_path_abs``
    (coalesced across image / video, empty string when neither), then ``created_at``,
    then ``sample_id`` as a unique final tiebreaker.
    """
    file_path_abs = sqlalchemy.func.coalesce(
        col(ImageTable.file_path_abs),
        col(VideoTable.file_path_abs),
        "",
    )
    return [
        (file_path_abs, True),
        (cast(ColumnElement[Any], col(AnnotationBaseTable.created_at)), True),
        (cast(ColumnElement[Any], col(AnnotationBaseTable.sample_id)), True),
    ]


def _keyset_sample_id_query(filters: AnnotationsFilter) -> SelectOfScalar[UUID]:
    """Select annotation ``sample_id``s, joined to their parent media, with filters."""
    query: SelectOfScalar[UUID] = select(col(AnnotationBaseTable.sample_id)).select_from(
        AnnotationBaseTable
    )
    return filters.apply(_join_parent_media(query))


def _fetch_anchor_values(
    session: Session,
    sample_id: UUID,
    filters: AnnotationsFilter,
    sort_keys: list[keyset_seek.SortKey],
) -> tuple[Any, ...] | None:
    """Return the annotation's sort-key values, or ``None`` if it is filtered out."""
    query: SelectOfScalar[Any] = _join_parent_media(
        select(*[column for column, _ in sort_keys]).select_from(AnnotationBaseTable)
    )
    query = filters.apply(query).where(col(AnnotationBaseTable.sample_id) == sample_id)

    row = session.exec(query).first()
    if row is None:
        return None
    return tuple(row)


def _join_parent_media(query: SelectOfScalar[Any]) -> SelectOfScalar[Any]:
    """Outer-join the annotation's parent image / video frame / video for the sort keys."""
    return (
        query.outerjoin(
            ImageTable, col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id)
        )
        .outerjoin(
            VideoFrameTable,
            col(VideoFrameTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .outerjoin(
            VideoTable, col(VideoTable.sample_id) == col(VideoFrameTable.parent_sample_id)
        )
    )
