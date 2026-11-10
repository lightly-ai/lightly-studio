"""Start an object track from an existing cuboid of a sequence."""

from __future__ import annotations

import threading
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.annotation.object_track import ObjectTrackTable
from lightly_studio.resolvers import annotation_resolver, object_track_resolver, sequence_resolver
from lightly_studio.services.recording_service.get_ticks import get_ticks

_START_LOCK = threading.Lock()


def start_sequence_track(
    session: Session, dataset_id: UUID, sequence_id: UUID, annotation_id: UUID
) -> ObjectTrackTable | None:
    """Create a track and make an untracked cuboid its first annotation.

    A row lock claims the cuboid while its track is created and attached in the same
    transaction, so concurrent requests cannot claim it or leave an empty track.

    Args:
        session: The database session.
        dataset_id: The dataset the sequence must belong to.
        sequence_id: The sequence sample ID.
        annotation_id: The cuboid to start the track from.

    Returns:
        The new track, or `None` if the sequence is not part of the dataset.

    Raises:
        ValueError: If the annotation is not a cuboid of a tick of this sequence, or it
            already belongs to a track.
    """
    if get_ticks(session=session, dataset_id=dataset_id, sequence_id=sequence_id) is None:
        return None
    with _START_LOCK:
        annotation = annotation_resolver.get_by_id(session=session, annotation_id=annotation_id)
        if annotation is None or annotation.annotation_type != AnnotationType.CUBOID_3D:
            raise ValueError(f"Cuboid annotation {annotation_id} not found.")
        link = sequence_resolver.get_link_by_sample_id(
            session=session, sample_id=annotation.parent_sample_id
        )
        if link is None or link.sequence_sample_id != sequence_id:
            raise ValueError(
                f"Annotation {annotation_id} is not on a tick of sequence {sequence_id}."
            )
        annotation_query = select(AnnotationBaseTable).where(
            col(AnnotationBaseTable.sample_id) == annotation_id
        )
        if session.get_bind().dialect.name == "postgresql":
            annotation_query = annotation_query.with_for_update()
        locked_annotation = session.exec(
            annotation_query.execution_options(populate_existing=True)
        ).first()
        if locked_annotation is None:
            raise ValueError(f"Cuboid annotation {annotation_id} not found.")
        if locked_annotation.object_track_id is not None:
            raise ValueError(f"Annotation {annotation_id} already belongs to a track.")

        try:
            track = object_track_resolver.create_with_next_number(
                session=session, dataset_id=dataset_id, commit=False
            )
            object_track_resolver.add_annotation_to_object_track(
                session=session,
                annotation_id=annotation_id,
                object_track_id=track.object_track_id,
                commit=False,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        return track
