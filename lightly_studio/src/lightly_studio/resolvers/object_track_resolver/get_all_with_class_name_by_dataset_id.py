"""Get all object tracks for a dataset with their annotation class names."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.object_track import ObjectTrackTable, TrackWithClassNameView
from lightly_studio.models.annotation_label import AnnotationLabelTable


def get_all_with_class_name_by_dataset_id(
    session: Session,
    dataset_id: UUID,
) -> list[TrackWithClassNameView]:
    """Retrieve all object tracks for a dataset, each enriched with its class name.

    The class name is derived from the annotation label of the first annotation
    belonging to the track. Tracks without annotations have a ``None`` class name.
    """
    tracks = session.exec(
        select(ObjectTrackTable).where(col(ObjectTrackTable.dataset_id) == dataset_id)
    ).all()
    if not tracks:
        return []

    track_ids = [t.object_track_id for t in tracks]

    # Fetch one (class_name, track_id) pair per track in a single query using
    # DISTINCT ON equivalent: group by track_id and pick any label name.
    rows = session.exec(
        select(
            col(AnnotationBaseTable.object_track_id),
            func.min(col(AnnotationLabelTable.annotation_label_name)),
        )
        .join(
            AnnotationLabelTable,
            col(AnnotationBaseTable.annotation_label_id)
            == col(AnnotationLabelTable.annotation_label_id),
        )
        .where(col(AnnotationBaseTable.object_track_id).in_(track_ids))
        .group_by(col(AnnotationBaseTable.object_track_id))
    ).all()

    class_name_by_track: dict[UUID, str] = {row[0]: row[1] for row in rows if row[0] is not None}

    return [
        TrackWithClassNameView(
            object_track_id=t.object_track_id,
            object_track_number=t.object_track_number,
            annotation_class_name=class_name_by_track.get(t.object_track_id),
        )
        for t in tracks
    ]
