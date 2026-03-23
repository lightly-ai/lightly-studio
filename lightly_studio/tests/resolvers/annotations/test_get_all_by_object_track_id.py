"""Tests for get_all_by_object_track_id resolver."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
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
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    dataset_id = collection.collection_id
    label = create_annotation_label(
        session=db_session, root_collection_id=dataset_id, label_name="label"
    )

    img_1 = create_image(session=db_session, collection_id=dataset_id, file_path_abs="/tmp/1.png")

    track_ids = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=dataset_id),
            ObjectTrackCreate(object_track_number=2, dataset_id=dataset_id),
        ],
    )
    track_a, track_b = track_ids

    annotations = create_annotations(
        session=db_session,
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
        session=db_session, object_track_id=track_a
    )
    assert len(result) == 2
    assert {annotation.sample_id for annotation in result} == {
        track_a_annotations[0].sample_id,
        track_a_annotations[1].sample_id,
    }


def test_get_all_by_object_track_id__filter_by_annotation_type(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    dataset_id = collection.collection_id
    label = create_annotation_label(
        session=db_session, root_collection_id=dataset_id, label_name="label"
    )

    image_sample = create_image(
        session=db_session, collection_id=dataset_id, file_path_abs="/tmp/1.png"
    )

    track_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=dataset_id),
        ],
    )[0]

    annotations = create_annotations(
        session=db_session,
        collection_id=dataset_id,
        annotations=[
            AnnotationDetails(
                sample_id=image_sample.sample_id,
                annotation_label_id=label.annotation_label_id,
                object_track_id=track_id,
            ),
            AnnotationDetails(
                sample_id=image_sample.sample_id,
                annotation_label_id=label.annotation_label_id,
                object_track_id=track_id,
                annotation_type=AnnotationType.SEMANTIC_SEGMENTATION,
            ),
            AnnotationDetails(
                sample_id=image_sample.sample_id,
                annotation_label_id=label.annotation_label_id,
                object_track_id=track_id,
            ),
        ],
    )
    result = annotation_resolver.get_all_by_object_track_id(
        session=db_session,
        object_track_id=track_id,
        annotation_types=[AnnotationType.SEMANTIC_SEGMENTATION],
    )
    assert len(result) == 1
    assert {annotation.sample_id for annotation in result} == {
        annotations[1].sample_id,
    }
