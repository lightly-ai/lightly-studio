"""Resolver for getting adjacent annotations for a given annotation ID."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.dataset_query.order_by import OrderByAnnotationEvaluationMetricField
from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.resolvers.annotation_resolver.get_adjacent_annotations_window import (
    get_adjacent_annotations_window,
)
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter


def get_adjacent_annotations(
    session: Session,
    sample_id: UUID,
    filters: AnnotationsFilter,
    order_by: OrderByAnnotationEvaluationMetricField | None = None,
) -> AdjacentResultView | None:
    """Get the adjacent annotations for a given annotation ID.

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

    return get_adjacent_annotations_window(
        session=session,
        sample_id=sample_id,
        filters=filters,
        order_by=order_by,
    )
