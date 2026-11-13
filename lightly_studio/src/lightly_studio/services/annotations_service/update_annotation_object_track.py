"""Update the object track assignment of an annotation."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    object_track_resolver,
)
from lightly_studio.resolvers.annotation_resolver import annotation_helper


def update_annotation_object_track(
    session: Session,
    annotation_id: UUID,
    collection_id: UUID,
    object_track_id: UUID | None,
    create_new_track: bool = False,
) -> AnnotationBaseTable:
    """Update the object track assignment of an annotation.

    When ``create_new_track`` is set, a new track is created and the annotation
    is linked to it. When the annotation is removed from a track and no other
    annotations or child tracks remain, the track is automatically deleted.

    Args:
        session: Database session for executing the operation.
        annotation_id: UUID of the annotation to update.
        collection_id: UUID of the annotation's collection, used to resolve
            the dataset when creating a new track.
        object_track_id: UUID of the target track, or None to remove the
            annotation from its current track.
        create_new_track: If True, create a new track and assign the
            annotation to it. ``object_track_id`` must be None.

    Returns:
        The updated annotation.
    """
    if create_new_track and object_track_id is not None:
        raise ValueError("Cannot set both create_new_track and object_track_id.")

    annotation = annotation_resolver.get_by_id(session=session, annotation_id=annotation_id)
    if annotation is None:
        raise ValueError(f"Annotation with id {annotation_id} does not exist.")

    if object_track_id is not None:
        _validate_object_track(
            session=session,
            object_track_id=object_track_id,
            collection_id=collection_id,
        )

    if create_new_track:
        object_track_id = _create_track(session=session, collection_id=collection_id)

    old_track_id = annotation.object_track_id
    _assign_track(session=session, annotation=annotation, object_track_id=object_track_id)
    if old_track_id is not None and old_track_id != object_track_id:
        _delete_empty_track(session=session, object_track_id=old_track_id)
    updated = annotation_resolver.get_by_id(session=session, annotation_id=annotation_id)
    if updated is None:
        raise RuntimeError(f"Annotation {annotation_id} disappeared after update.")
    return updated


def _create_track(session: Session, collection_id: UUID) -> UUID:
    """Create a track with the next number in the annotation source's dataset."""
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None:
        raise ValueError(f"Annotation source {collection_id} not found.")
    track_number = object_track_resolver.next_track_number(
        session=session, dataset_id=collection.dataset_id
    )
    return object_track_resolver.create_many(
        session=session,
        tracks=[
            ObjectTrackCreate(object_track_number=track_number, dataset_id=collection.dataset_id)
        ],
    )[0]


def _assign_track(
    session: Session, annotation: AnnotationBaseTable, object_track_id: UUID | None
) -> AnnotationBaseTable:
    """Assign a track with cuboid validation, or remove the current assignment."""
    if object_track_id is not None:
        return object_track_resolver.add_annotation_to_object_track(
            session=session, annotation_id=annotation.sample_id, object_track_id=object_track_id
        )
    return annotation_helper.update_annotation_object(
        session=session, annotation=annotation, fields_to_update={"object_track_id": None}
    )


def _validate_object_track(session: Session, object_track_id: UUID, collection_id: UUID) -> None:
    """Raise if the track does not exist or belongs to a different dataset."""
    track = object_track_resolver.get_by_id(session=session, object_track_id=object_track_id)
    if track is None:
        raise ValueError(f"Object track {object_track_id} not found.")
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None:
        raise ValueError(f"Collection {collection_id} not found.")
    if track.dataset_id != collection.dataset_id:
        raise ValueError(
            f"Object track {object_track_id} belongs to a different dataset"
            f" than collection {collection_id}."
        )


def _delete_empty_track(session: Session, object_track_id: UUID) -> None:
    """Delete a track after its last annotation is removed, preserving parent tracks."""
    remaining = annotation_resolver.get_all_by_object_track_id(
        session=session, object_track_id=object_track_id
    )
    if not remaining:
        object_track_resolver.delete_by_id(session=session, object_track_id=object_track_id)
