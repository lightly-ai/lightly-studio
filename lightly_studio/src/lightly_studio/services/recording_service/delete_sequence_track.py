"""Delete an object track of a sequence together with its cuboids."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import annotation_resolver, object_track_resolver
from lightly_studio.services.recording_service.extend_sequence_track import find_sequence_track
from lightly_studio.services.recording_service.get_ticks import get_ticks


def delete_sequence_track(
    session: Session,
    dataset_id: UUID,
    sequence_id: UUID,
    track_id: UUID,
    annotation_source_id: UUID,
) -> int | None:
    """Delete the track's cuboids in one annotation source of the sequence.

    The track record itself is removed once no annotations or child tracks refer to it.
    A track that still has cuboids in another source or sequence is kept. Deleting
    annotations is not one database transaction, so a failure can leave some cuboids deleted.

    Args:
        session: The database session.
        dataset_id: The dataset the sequence must belong to.
        sequence_id: The sequence sample ID.
        track_id: The track to delete.
        annotation_source_id: The annotation source whose cuboids of the track are deleted.

    Returns:
        The number of deleted cuboids, or `None` if the sequence does not exist or does not
        belong to `dataset_id`.

    Raises:
        ValueError: If the track has no annotations from this source in the sequence.
    """
    if get_ticks(session=session, dataset_id=dataset_id, sequence_id=sequence_id) is None:
        return None
    track = find_sequence_track(
        session=session,
        dataset_id=dataset_id,
        sequence_id=sequence_id,
        track_id=track_id,
        annotation_source_id=annotation_source_id,
    )
    deleted = annotation_resolver.delete_annotations_by_ids(
        session=session,
        annotation_ids=[annotation.annotation_id for annotation in track.annotations],
    )
    object_track_resolver.delete_empty_by_ids(session=session, object_track_ids=[track_id])
    return deleted
