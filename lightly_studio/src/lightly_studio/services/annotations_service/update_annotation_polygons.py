"""Update the polygons of a polygon annotation."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.polygon import Polygons
from lightly_studio.resolvers import annotation_resolver, evaluation_run_resolver


def update_annotation_polygons(
    session: Session, annotation_id: UUID, polygons: Polygons
) -> AnnotationBaseTable:
    """Replace the polygons of an annotation and mark its evaluation runs stale.

    Args:
        session: Database session.
        annotation_id: The annotation ID to update.
        polygons: The new polygon parts. Each part is a list of (x, y) vertices.

    Returns:
        The updated AnnotationBaseTable instance.
    """
    result = annotation_resolver.update_polygons(
        session=session, annotation_id=annotation_id, polygons=polygons
    )
    evaluation_run_resolver.mark_stale_by_collection_id(
        session=session,
        collection_id=result.annotation_collection_id,
    )
    return result
