"""Start an object track from an existing cuboid of a sequence."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.annotation.object_track import ObjectTrackTable
from lightly_studio.resolvers import annotation_resolver, object_track_resolver, sequence_resolver
from lightly_studio.services.recording_service.get_ticks import get_ticks


def start_sequence_track(
    session: Session, dataset_id: UUID, sequence_id: UUID, annotation_id: UUID
) -> ObjectTrackTable | None:
    """Create a track and make an untracked cuboid its first annotation.

    The cuboid is checked before the track is created, and the track is deleted again if
    the cuboid cannot be attached, so a failed request leaves no empty track. Attaching a
    cuboid is not one database transaction, so the track is removed explicitly.

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
    annotation = annotation_resolver.get_by_id(session=session, annotation_id=annotation_id)
    if annotation is None or annotation.annotation_type != AnnotationType.CUBOID_3D:
        raise ValueError(f"Cuboid annotation {annotation_id} not found.")
    link = sequence_resolver.get_link_by_sample_id(
        session=session, sample_id=annotation.parent_sample_id
    )
    if link is None or link.sequence_sample_id != sequence_id:
        raise ValueError(f"Annotation {annotation_id} is not on a tick of sequence {sequence_id}.")
    if annotation.object_track_id is not None:
        raise ValueError(f"Annotation {annotation_id} already belongs to a track.")

    track = object_track_resolver.create_with_next_number(session=session, dataset_id=dataset_id)
    try:
        object_track_resolver.add_annotation_to_object_track(
            session=session, annotation_id=annotation_id, object_track_id=track.object_track_id
        )
    except Exception:
        session.rollback()
        object_track_resolver.delete_by_id(session=session, object_track_id=track.object_track_id)
        raise
    return track
