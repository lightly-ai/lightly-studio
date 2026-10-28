"""Tests for update_label_by_object_track_id resolver."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.resolvers import annotation_resolver, object_track_resolver
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
)


def test_update_label_by_object_track_id(db_session: Session) -> None:
    """All sibling annotations in the track receive the new label."""
    collection = create_collection(session=db_session)
    root_collection_id = collection.collection_id
    old_label = create_annotation_label(
        session=db_session, root_collection_id=root_collection_id, label_name="cat"
    )
    new_label = create_annotation_label(
        session=db_session, root_collection_id=root_collection_id, label_name="dog"
    )

    img_1 = create_image(
        session=db_session, collection_id=root_collection_id, file_path_abs="/tmp/1.png"
    )
    img_2 = create_image(
        session=db_session, collection_id=root_collection_id, file_path_abs="/tmp/2.png"
    )

    track_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id)],
    )[0]

    annotations = create_annotations(
        session=db_session,
        collection_id=root_collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=img_1.sample_id,
                annotation_label_id=old_label.annotation_label_id,
                object_track_id=track_id,
                x=10,
                y=20,
                width=30,
                height=40,
            ),
            AnnotationDetails(
                sample_id=img_2.sample_id,
                annotation_label_id=old_label.annotation_label_id,
                object_track_id=track_id,
                x=50,
                y=60,
                width=70,
                height=80,
            ),
        ],
    )

    annotation_resolver.update_label_by_object_track_id(
        session=db_session,
        object_track_id=track_id,
        annotation_label_id=new_label.annotation_label_id,
    )

    updated_1 = annotation_resolver.get_by_id(
        session=db_session, annotation_id=annotations[0].sample_id
    )
    updated_2 = annotation_resolver.get_by_id(
        session=db_session, annotation_id=annotations[1].sample_id
    )

    assert updated_1 is not None
    assert updated_1.annotation_label_id == new_label.annotation_label_id
    assert updated_1.object_detection_details is not None
    assert updated_1.object_detection_details.x == 10
    assert updated_1.object_detection_details.y == 20
    assert updated_1.object_detection_details.width == 30
    assert updated_1.object_detection_details.height == 40

    assert updated_2 is not None
    assert updated_2.annotation_label_id == new_label.annotation_label_id
    assert updated_2.object_detection_details is not None
    assert updated_2.object_detection_details.x == 50
    assert updated_2.object_detection_details.y == 60
    assert updated_2.object_detection_details.width == 70
    assert updated_2.object_detection_details.height == 80


def test_update_label_by_object_track_id__invalid_label_raises_before_deleting_children(
    db_session: Session,
) -> None:
    """ValueError is raised and no child rows are deleted when the label does not exist."""
    collection = create_collection(session=db_session)
    root_collection_id = collection.collection_id
    label = create_annotation_label(
        session=db_session, root_collection_id=root_collection_id, label_name="cat"
    )

    img = create_image(
        session=db_session, collection_id=root_collection_id, file_path_abs="/tmp/1.png"
    )

    track_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id)],
    )[0]

    annotations = create_annotations(
        session=db_session,
        collection_id=root_collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=img.sample_id,
                annotation_label_id=label.annotation_label_id,
                object_track_id=track_id,
                x=10,
                y=20,
                width=30,
                height=40,
            ),
        ],
    )
    nonexistent_label_id = uuid4()

    with pytest.raises(ValueError, match=str(nonexistent_label_id)):
        annotation_resolver.update_label_by_object_track_id(
            session=db_session,
            object_track_id=track_id,
            annotation_label_id=nonexistent_label_id,
        )

    # Child rows must still be present — no data was deleted.
    unchanged = annotation_resolver.get_by_id(
        session=db_session, annotation_id=annotations[0].sample_id
    )
    assert unchanged is not None
    assert unchanged.annotation_label_id == label.annotation_label_id
    assert unchanged.object_detection_details is not None
    assert unchanged.object_detection_details.x == 10
    assert unchanged.object_detection_details.y == 20
    assert unchanged.object_detection_details.width == 30
    assert unchanged.object_detection_details.height == 40
