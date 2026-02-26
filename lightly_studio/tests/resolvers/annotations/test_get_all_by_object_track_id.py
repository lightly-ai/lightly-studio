"""Tests for get_all_by_object_track_id resolver."""

from __future__ import annotations

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


def test_get_all_by_object_track_id_returns_only_track_annotations(
    test_db: Session,
) -> None:
    collection = create_collection(session=test_db)
    dataset_id = collection.collection_id
    label = create_annotation_label(session=test_db, dataset_id=dataset_id, label_name="label")

    img_1 = create_image(session=test_db, collection_id=dataset_id, file_path_abs="/tmp/1.png")

    track_ids = object_track_resolver.create_many(
        session=test_db,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=dataset_id),
            ObjectTrackCreate(object_track_number=2, dataset_id=dataset_id),
        ],
    )
    track_a, track_b = track_ids

    annotations = create_annotations(
        session=test_db,
        collection_id=dataset_id,
        annotations=[
            AnnotationDetails(
                sample_id=img_1.sample_id,
                annotation_label_id=label.annotation_label_id,
                object_track_id=track_a,
            ),
            AnnotationDetails(
                sample_id=img_1.sample_id,
                annotation_label_id=label.annotation_label_id,
                object_track_id=track_a,
            ),
            AnnotationDetails(
                sample_id=img_1.sample_id,
                annotation_label_id=label.annotation_label_id,
                object_track_id=track_b,
            ),
        ],
    )
    track_a_annotations = [
        annotation for annotation in annotations if annotation.object_track_id == track_a
    ]
    assert len(track_a_annotations) == 2
    result = annotation_resolver.get_all_by_object_track_id(
        session=test_db, object_track_id=track_a
    )
    assert len(result) == 2
    assert {annotation.sample_id for annotation in result} == {
        track_a_annotations[0].sample_id,
        track_a_annotations[1].sample_id,
    }
