"""Update the parent track of an object track.

DuckDB treats UPDATE as delete+insert, which fails when annotation_base rows
reference the track via a foreign key. We work around this by creating a
replacement track and moving all annotations to it, reusing the same
delete-and-reinsert pattern the codebase already uses for annotation mutations.
"""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.object_track import ObjectTrackCreate, ObjectTrackTable
from lightly_studio.resolvers import annotation_resolver, object_track_resolver
from lightly_studio.resolvers.annotation_resolver import annotation_helper


def update_parent_track(
    session: Session,
    dataset_id: UUID,
    object_track_id: UUID,
    parent_object_track_id: UUID | None,
) -> ObjectTrackTable | None:
    """Set or remove the parent track relationship.

    Creates a replacement track with the updated parent and moves all
    annotations from the old track to the new one. The old track is deleted
    after the last annotation is moved.

    Args:
        session: Database session for executing the operation.
        dataset_id: UUID of the dataset the track must belong to.
        object_track_id: UUID of the track to update.
        parent_object_track_id: UUID of the new parent track, or None to remove.

    Returns:
        The replacement track, or None if the track was not found in the dataset.

    Raises:
        ValueError: If the parent is missing, belongs to another dataset, or
            the assignment would create a self-reference or cycle.
    """
    track = object_track_resolver.get_by_id(session=session, object_track_id=object_track_id)
    if track is None or track.dataset_id != dataset_id:
        return None

    if parent_object_track_id is not None:
        _validate_parent_track(
            session=session,
            object_track_id=object_track_id,
            parent_object_track_id=parent_object_track_id,
            dataset_id=track.dataset_id,
        )

    if track.parent_object_track_id == parent_object_track_id:
        return track

    new_track_id = _create_replacement_track(
        session=session, track=track, parent_object_track_id=parent_object_track_id
    )
    _migrate_annotations(
        session=session, object_track_id=object_track_id, new_track_id=new_track_id
    )
    _migrate_descendants(
        session=session,
        dataset_id=dataset_id,
        object_track_id=object_track_id,
        new_track_id=new_track_id,
    )
    object_track_resolver.delete_by_id(session=session, object_track_id=object_track_id)

    return object_track_resolver.get_by_id(session=session, object_track_id=new_track_id)


def _validate_parent_track(
    session: Session, dataset_id: UUID, object_track_id: UUID, parent_object_track_id: UUID
) -> None:
    """Validate parent ownership and reject self-references and cycles before mutation."""
    if parent_object_track_id == object_track_id:
        raise ValueError("A track cannot be its own parent")

    parent = object_track_resolver.get_by_id(
        session=session, object_track_id=parent_object_track_id
    )
    if parent is None or parent.dataset_id != dataset_id:
        raise ValueError("Parent track not found in the dataset.")

    _check_no_cycle(
        session=session,
        dataset_id=dataset_id,
        object_track_id=object_track_id,
        parent_object_track_id=parent_object_track_id,
    )


def _create_replacement_track(
    session: Session, track: ObjectTrackTable, parent_object_track_id: UUID | None
) -> UUID:
    """Copy track properties into a replacement with the requested parent."""
    return object_track_resolver.create_many(
        session=session,
        tracks=[
            ObjectTrackCreate(
                object_track_number=track.object_track_number,
                dataset_id=track.dataset_id,
                source_track_id=track.source_track_id,
                parent_object_track_id=parent_object_track_id,
            )
        ],
    )[0]


def _migrate_annotations(session: Session, object_track_id: UUID, new_track_id: UUID) -> None:
    """Move all annotations from the old track to its replacement."""
    annotations = annotation_resolver.get_all_by_object_track_id(
        session=session,
        object_track_id=object_track_id,
    )
    for annotation in annotations:
        annotation_helper.update_annotation_object(
            session=session,
            annotation=annotation,
            fields_to_update={"object_track_id": new_track_id},
        )


def _migrate_descendants(
    session: Session, dataset_id: UUID, object_track_id: UUID, new_track_id: UUID
) -> None:
    """Re-parent child tracks and migrate their descendants recursively."""
    child_tracks = session.exec(
        select(ObjectTrackTable).where(
            col(ObjectTrackTable.parent_object_track_id) == object_track_id
        )
    ).all()
    for child in child_tracks:
        update_parent_track(
            session=session,
            dataset_id=dataset_id,
            object_track_id=child.object_track_id,
            parent_object_track_id=new_track_id,
        )


def _check_no_cycle(
    session: Session,
    object_track_id: UUID,
    parent_object_track_id: UUID,
    dataset_id: UUID,
) -> None:
    """Raise if setting the parent would create a circular reference.

    Fetches all tracks for the dataset in one query, then walks the ancestor
    chain from the proposed parent. If the walk reaches ``object_track_id``,
    the assignment would form a cycle.
    """
    all_tracks = session.exec(
        select(ObjectTrackTable).where(col(ObjectTrackTable.dataset_id) == dataset_id)
    ).all()
    parent_by_id: dict[UUID, UUID | None] = {
        t.object_track_id: t.parent_object_track_id for t in all_tracks
    }

    current: UUID | None = parent_object_track_id
    while current is not None:
        if current == object_track_id:
            raise ValueError("Setting this parent would create a circular reference")
        current = parent_by_id.get(current)
