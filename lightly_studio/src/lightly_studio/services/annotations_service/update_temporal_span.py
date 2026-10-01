"""Update the temporal span (start/end time) of an annotation."""

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
    """Retrieve an annotation by its ID and update its temporal span.

    Args:
        session: Database session.
        annotation_id: The annotation ID to update.
        start_time_s: The new start time in seconds.
        end_time_s: The new end time in seconds.

    Returns:
        The updated AnnotationBaseTable instance.
    """
    return annotation_resolver.update_temporal_span(
        session=session,
        annotation_id=annotation_id,
        start_time_s=start_time_s,
        end_time_s=end_time_s,
    )
