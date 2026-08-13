"""Resolver for getting adjacent annotations for a given annotation ID."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.dataset_query.order_by import OrderByAnnotationEvaluationMetricField
from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver
from lightly_studio.resolvers.annotation_resolver.get_adjacent_annotations_keyset import (
    get_adjacent_annotations_keyset,
)
from lightly_studio.resolvers.annotation_resolver.get_adjacent_annotations_window import (
    get_adjacent_annotations_window,
)
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter

# Parent sample types whose file path is a plain column on a single table, so the keyset
# seek can drive an index range scan over it.
_KEYSET_PARENT_SAMPLE_TYPES = (SampleType.IMAGE, SampleType.VIDEO_FRAME)


def get_adjacent_annotations(
    session: Session,
    sample_id: UUID,
    filters: AnnotationsFilter,
    order_by: OrderByAnnotationEvaluationMetricField | None = None,
) -> AdjacentResultView | None:
    """Get the adjacent annotations for a given annotation ID.

    Uses a keyset (seek) lookup when the annotations' parent kind is known, so prev/next
    and the position/total counts avoid sorting and windowing the whole collection.
    Everything else falls back to the window-function implementation.

    Args:
        session: Database session.
        sample_id: The anchor annotation whose neighbours we want.
        filters: Annotation filters constraining the set; must scope the collection.
        order_by: Optional leading sort key applied before the tiebreaker chain.

    Returns:
        The adjacency result, or ``None`` if the anchor is not in the filtered set.

    Raises:
        ValueError: If the filters do not scope the collection.
    """
    if not filters.collection_ids:
        raise ValueError("Collection IDs must be provided in filters.")

    parent_sample_type = _keyset_parent_sample_type(session=session, filters=filters)
    if parent_sample_type is not None:
        return get_adjacent_annotations_keyset(
            session=session,
            sample_id=sample_id,
            filters=filters,
            parent_sample_type=parent_sample_type,
        )

    return get_adjacent_annotations_window(
        session=session,
        sample_id=sample_id,
        filters=filters,
        order_by=order_by,
    )


def _keyset_parent_sample_type(
    session: Session,
    filters: AnnotationsFilter,
) -> SampleType | None:
    """Return the parent sample type the keyset path can serve, or ``None``.

    The keyset path joins exactly one parent table, so it needs a single annotation
    collection with a supported parent kind. Spanning several collections could mix parent
    kinds, so those requests keep the window implementation.
    """
    if filters.collection_ids is None or len(filters.collection_ids) != 1:
        return None

    parent_collection = collection_resolver.get_parent_collection_id(
        session=session, collection_id=filters.collection_ids[0]
    )
    if parent_collection is None:
        return None
    if parent_collection.sample_type not in _KEYSET_PARENT_SAMPLE_TYPES:
        return None
    return parent_collection.sample_type
