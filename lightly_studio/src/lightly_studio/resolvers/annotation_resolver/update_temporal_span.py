"""Module for updating the temporal span (start/end time) of an annotation."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.resolvers import annotation_resolver


def update_temporal_span(
    session: Session,
    annotation_id: UUID,
    start_time_s: float,
    end_time_s: float,
) -> AnnotationBaseTable:
    """Update the temporal span of an annotation.

    Args:
        session: Database session for executing the operation.
        annotation_id: UUID of the annotation to update.
        start_time_s: New start time in seconds.
        end_time_s: New end time in seconds.

    Returns:
        The updated annotation with the new temporal span.

    Raises:
        ValueError: If the annotation is not found, has no temporal span, or the
            span is invalid.
    """
    if start_time_s < 0:
        raise ValueError("start_time_s must be non-negative.")
    if start_time_s >= end_time_s:
        raise ValueError("start_time_s must be less than end_time_s.")

    annotation = annotation_resolver.get_by_id(session=session, annotation_id=annotation_id)
    if not annotation:
        raise ValueError(f"Annotation with ID {annotation_id} not found.")
    if annotation.temporal_span_details is None:
        raise ValueError("Annotation does not have a temporal span to update.")

    try:
        annotation.temporal_span_details.start_time_s = start_time_s
        annotation.temporal_span_details.end_time_s = end_time_s
        session.add(annotation.temporal_span_details)
        session.commit()
        session.refresh(annotation)
        return annotation
    except Exception:
        session.rollback()
        raise
