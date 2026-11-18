"""Tests for update_annotation_object_track service."""

from __future__ import annotations

import sys
import uuid

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.resolvers import annotation_resolver, collection_resolver, object_track_resolver
from lightly_studio.resolvers.annotation_resolver import annotation_helper
from lightly_studio.services import annotations_service
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_groups,
    create_image,
    cuboid_create,
)


def test_update_annotation_object_track__reassign_to_existing_track(db_session: Session) -> None:
    """Reassigning an annotation moves it to the target track."""
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)

    track_a_id, track_b_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id),
            ObjectTrackCreate(object_track_number=2, dataset_id=collection.dataset_id),
        ],
    )

    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    annotation_id = annotation.sample_id

    object_track_resolver.add_annotation_to_object_track(
        session=db_session,
        annotation_id=annotation_id,
        object_track_id=track_a_id,
    )

    result = annotations_service.update_annotation_object_track(
        session=db_session,
        annotation_id=annotation_id,
        collection_id=collection.collection_id,
        object_track_id=track_b_id,
    )

    assert result.object_track_id == track_b_id
    assert result.object_track is not None
    assert result.object_track.object_track_id == track_b_id
    fetched = annotation_resolver.get_by_id(session=db_session, annotation_id=annotation_id)
    assert fetched is not None
    assert fetched.object_track_id == track_b_id


def test_update_annotation_object_track__remove_track_assignment(db_session: Session) -> None:
    """Setting object_track_id to None removes the annotation from its track."""
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)

    track_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id),
        ],
    )[0]

    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    annotation_id = annotation.sample_id

    object_track_resolver.add_annotation_to_object_track(
        session=db_session,
        annotation_id=annotation_id,
        object_track_id=track_id,
    )

    result = annotations_service.update_annotation_object_track(
        session=db_session,
        annotation_id=annotation_id,
        collection_id=collection.collection_id,
        object_track_id=None,
    )

    assert result.object_track_id is None


def test_update_annotation_object_track__empty_track_auto_deleted(db_session: Session) -> None:
    """A track with no remaining annotations is deleted after reassignment."""
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)

    track_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id),
        ],
    )[0]

    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    annotation_id = annotation.sample_id

    object_track_resolver.add_annotation_to_object_track(
        session=db_session,
        annotation_id=annotation_id,
        object_track_id=track_id,
    )

    annotations_service.update_annotation_object_track(
        session=db_session,
        annotation_id=annotation_id,
        collection_id=collection.collection_id,
        object_track_id=None,
    )

    assert object_track_resolver.get_by_id(session=db_session, object_track_id=track_id) is None


def test_update_annotation_object_track__sibling_annotations_unaffected(
    db_session: Session,
) -> None:
    """Reassigning one annotation does not move siblings in the old track."""
    collection = create_collection(session=db_session)
    image_a = create_image(session=db_session, collection_id=collection.collection_id)
    image_b = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)

    track_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id),
        ],
    )[0]

    annotation_a = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image_a.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    annotation_a_id = annotation_a.sample_id
    annotation_b = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image_b.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    annotation_b_id = annotation_b.sample_id

    object_track_resolver.add_annotation_to_object_track(
        session=db_session,
        annotation_id=annotation_a_id,
        object_track_id=track_id,
    )
    object_track_resolver.add_annotation_to_object_track(
        session=db_session,
        annotation_id=annotation_b_id,
        object_track_id=track_id,
    )

    annotations_service.update_annotation_object_track(
        session=db_session,
        annotation_id=annotation_a_id,
        collection_id=collection.collection_id,
        object_track_id=None,
    )

    sibling = annotation_resolver.get_by_id(session=db_session, annotation_id=annotation_b_id)
    assert sibling is not None
    assert sibling.object_track_id == track_id
    # Track still exists because the sibling remains.
    assert object_track_resolver.get_by_id(session=db_session, object_track_id=track_id) is not None


def test_update_annotation_object_track__create_new_track(db_session: Session) -> None:
    """Setting create_new_track creates a track and assigns the annotation."""
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)

    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    annotation_id = annotation.sample_id

    result = annotations_service.update_annotation_object_track(
        session=db_session,
        annotation_id=annotation_id,
        collection_id=collection.collection_id,
        object_track_id=None,
        create_new_track=True,
    )

    assert result.object_track_id is not None
    track = object_track_resolver.get_by_id(
        session=db_session, object_track_id=result.object_track_id
    )
    assert track is not None
    assert track.dataset_id == collection.dataset_id


def test_update_annotation_object_track__create_new_track_with_object_track_id_raises(
    db_session: Session,
) -> None:
    """Setting both create_new_track and object_track_id raises ValueError."""
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )

    with pytest.raises(ValueError, match="Cannot set both"):
        annotations_service.update_annotation_object_track(
            session=db_session,
            annotation_id=annotation.sample_id,
            collection_id=collection.collection_id,
            object_track_id=uuid.uuid4(),
            create_new_track=True,
        )


def test_update_annotation_object_track__create_new_track_uses_next_track_number(
    db_session: Session,
) -> None:
    """A newly created track gets the next track number after existing tracks."""
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)

    object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id),
            ObjectTrackCreate(object_track_number=5, dataset_id=collection.dataset_id),
        ],
    )

    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )

    result = annotations_service.update_annotation_object_track(
        session=db_session,
        annotation_id=annotation.sample_id,
        collection_id=collection.collection_id,
        object_track_id=None,
        create_new_track=True,
    )

    assert result.object_track_id is not None
    track = object_track_resolver.get_by_id(
        session=db_session, object_track_id=result.object_track_id
    )
    assert track is not None
    assert track.object_track_number == 6


def test_update_annotation_object_track__same_track_reassignment(db_session: Session) -> None:
    """Reassigning to the same track keeps the track and annotation intact."""
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)

    track_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id),
        ],
    )[0]

    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    annotation_id = annotation.sample_id

    object_track_resolver.add_annotation_to_object_track(
        session=db_session,
        annotation_id=annotation_id,
        object_track_id=track_id,
    )

    result = annotations_service.update_annotation_object_track(
        session=db_session,
        annotation_id=annotation_id,
        collection_id=collection.collection_id,
        object_track_id=track_id,
    )

    assert result.object_track_id == track_id
    assert object_track_resolver.get_by_id(session=db_session, object_track_id=track_id) is not None


def test_update_annotation_object_track__object_track_not_found(db_session: Session) -> None:
    """Supplying a non-existent object_track_id raises ValueError."""
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )

    with pytest.raises(ValueError, match="not found"):
        annotations_service.update_annotation_object_track(
            session=db_session,
            annotation_id=annotation.sample_id,
            collection_id=collection.collection_id,
            object_track_id=uuid.uuid4(),
        )


def test_update_annotation_object_track__cross_dataset_track_rejected(db_session: Session) -> None:
    """Assigning a track from a different dataset raises ValueError."""
    collection_a = create_collection(session=db_session)
    collection_b = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection_b.collection_id)
    label = create_annotation_label(
        session=db_session, root_collection_id=collection_b.collection_id
    )
    annotation = create_annotation(
        session=db_session,
        collection_id=collection_b.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    track_from_other_dataset = object_track_resolver.create_many(
        session=db_session,
        tracks=[ObjectTrackCreate(object_track_number=1, dataset_id=collection_a.dataset_id)],
    )[0]

    with pytest.raises(ValueError, match="different dataset"):
        annotations_service.update_annotation_object_track(
            session=db_session,
            annotation_id=annotation.sample_id,
            collection_id=collection_b.collection_id,
            object_track_id=track_from_other_dataset,
        )


def test_update_annotation_object_track__nonexistent_annotation_raises(db_session: Session) -> None:
    """Updating a nonexistent annotation raises ValueError."""
    with pytest.raises(ValueError, match="does not exist"):
        annotations_service.update_annotation_object_track(
            session=db_session,
            annotation_id=uuid.uuid4(),
            collection_id=uuid.uuid4(),
            object_track_id=None,
        )


def test_update_annotation_object_track__duplicate_cuboid_rejected(db_session: Session) -> None:
    """A group cannot contain two cuboids assigned to the same track."""
    collection_id, group_ids = create_groups(session=db_session)
    collection = collection_resolver.get_by_id(session=db_session, collection_id=collection_id)
    assert collection is not None
    label = create_annotation_label(session=db_session, root_collection_id=collection_id)
    track_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id)],
    )[0]
    annotation_ids = annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collection_id,
        annotations=[
            cuboid_create(
                parent_sample_id=group_ids[0],
                annotation_label_id=label.annotation_label_id,
                object_track_id=track_id,
            ),
            cuboid_create(
                parent_sample_id=group_ids[0], annotation_label_id=label.annotation_label_id
            ),
        ],
    )

    with pytest.raises(ValueError, match="A cuboid for this object track already exists"):
        annotations_service.update_annotation_object_track(
            session=db_session,
            annotation_id=annotation_ids[1],
            collection_id=collection_id,
            object_track_id=track_id,
        )

    annotation = annotation_resolver.get_by_id(session=db_session, annotation_id=annotation_ids[1])
    assert annotation is not None
    assert annotation.object_track_id is None


def test_update_annotation_object_track__parent_track_preserved(db_session: Session) -> None:
    """Removing a parent's last annotation preserves references from child tracks."""
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    parent_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id)],
    )[0]
    child_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(
                object_track_number=2,
                dataset_id=collection.dataset_id,
                parent_object_track_id=parent_id,
            )
        ],
    )[0]
    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    annotation_id = annotation.sample_id
    object_track_resolver.add_annotation_to_object_track(
        session=db_session, annotation_id=annotation_id, object_track_id=parent_id
    )

    result = annotations_service.update_annotation_object_track(
        session=db_session,
        annotation_id=annotation_id,
        collection_id=collection.collection_id,
        object_track_id=None,
    )

    assert result.object_track_id is None
    assert (
        object_track_resolver.get_by_id(session=db_session, object_track_id=parent_id) is not None
    )
    child = object_track_resolver.get_by_id(session=db_session, object_track_id=child_id)
    assert child is not None
    assert child.parent_object_track_id == parent_id


def test_update_annotation_object_track__annotation_disappeared_after_update(
    db_session: Session, mocker: MockerFixture
) -> None:
    """RuntimeError is raised when the annotation disappears between assign and re-fetch."""
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    annotation_id = annotation.sample_id

    original_get_by_id = annotation_resolver.get_by_id
    call_count = 0

    def get_by_id_then_none(
        session: Session, annotation_id: uuid.UUID
    ) -> AnnotationBaseTable | None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return original_get_by_id(session=session, annotation_id=annotation_id)
        return None

    mocker.patch.object(annotation_resolver, "get_by_id", side_effect=get_by_id_then_none)
    service_module = sys.modules[
        "lightly_studio.services.annotations_service.update_annotation_object_track"
    ]
    mocker.patch.object(service_module, "_assign_track")

    with pytest.raises(RuntimeError, match="disappeared after update"):
        annotations_service.update_annotation_object_track(
            session=db_session,
            annotation_id=annotation_id,
            collection_id=collection.collection_id,
            object_track_id=None,
        )


def test_update_annotation_object_track__track_deleted_during_reinsert(
    db_session: Session, mocker: MockerFixture
) -> None:
    """Annotation is preserved when the target track is deleted between delete and reinsert."""
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    track_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id)],
    )[0]
    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    annotation_id = annotation.sample_id

    original_delete = annotation_resolver.delete_annotation

    def delete_then_remove_track(
        session: Session, annotation_id: uuid.UUID, delete_sample: bool = True
    ) -> None:
        """Delete the annotation, then remove the track to simulate a concurrent deletion."""
        original_delete(session, annotation_id, delete_sample=delete_sample)
        object_track_resolver.delete_by_id(session=session, object_track_id=track_id)

    mocker.patch.object(
        annotation_resolver, "delete_annotation", side_effect=delete_then_remove_track
    )

    result = annotation_helper.update_annotation_object(
        session=db_session,
        annotation=annotation,
        fields_to_update={"object_track_id": track_id},
    )

    assert result.object_track_id is None
    fetched = annotation_resolver.get_by_id(session=db_session, annotation_id=annotation_id)
    assert fetched is not None
    assert fetched.object_track_id is None
