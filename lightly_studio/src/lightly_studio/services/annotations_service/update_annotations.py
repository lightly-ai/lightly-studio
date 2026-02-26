"""General annotation update service."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)
from lightly_studio.resolvers import annotation_resolver
from lightly_studio.services import annotations_service
from lightly_studio.services.annotations_service.update_annotation import AnnotationUpdate


def update_annotations(
    session: Session, annotation_updates: list[AnnotationUpdate]
) -> list[AnnotationBaseTable]:
    """Update multiple annotations.

    Args:
        session: Database session for executing the operation.
        annotation_updates: List of objects containing updates for the annotations.

    Info:
        If an annotation is part of an object track, this function updates the label for all
        annotations in the same object track. This is done to ensure that the label is
        consistent across all annotations in the track.

    Returns:
        List of updated annotations.
    """
    results: list[AnnotationBaseTable] = []
    track_target_label_ids: dict[UUID, UUID] = {}
    for annotation_update in annotation_updates:
        result = annotations_service.update_annotation(
            session,
            annotation_update,
        )
        results.append(result)

        if annotation_update.label_name is not None and result.object_track_id is not None:
            # Overwriting the value reflects the last input update for that track
            track_target_label_ids[result.object_track_id] = result.annotation_label_id

    # Update the label for all annotations in the track if needed
    for object_track_id, annotation_label_id in track_target_label_ids.items():
        siblings = annotation_resolver.get_all_by_object_track_id(
            session=session,
            object_track_id=object_track_id,
        )
        for sibling in siblings:
            if sibling.annotation_label_id == annotation_label_id:
                continue
            annotation_resolver.update_annotation_label(
                session=session,
                annotation_id=sibling.sample_id,
                annotation_label_id=annotation_label_id,
            )

    return results
