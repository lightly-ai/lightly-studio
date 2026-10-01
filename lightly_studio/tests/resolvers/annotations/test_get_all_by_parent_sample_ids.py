"""Tests for get_all_by_parent_sample_ids resolver."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
)


def test_get_all_by_parent_sample_ids(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="label",
    )
    image_b = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="sample_b.png",
    )
    image_a = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="sample_a.png",
    )

    annotations = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image_b.sample_id,
                annotation_label_id=label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image_a.sample_id,
                annotation_label_id=label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image_b.sample_id,
                annotation_label_id=label.annotation_label_id,
            ),
        ],
    )
    image_b_annotations = [
        annotation for annotation in annotations if annotation.parent_sample_id == image_b.sample_id
    ]

    result = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_session,
        parent_sample_ids=[
            image_b.sample_id,
        ],
    )
    assert len(result) == 2
    assert [annotation.sample_id for annotation in result] == [
        image_b_annotations[0].sample_id,
        image_b_annotations[1].sample_id,
    ]


def test_get_all_by_parent_sample_ids_with_no_parent_sample_ids_returns_empty_result(
    db_session: Session,
) -> None:
    result = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_session, parent_sample_ids=[]
    )

    assert result == []


def test_get_all_by_parent_sample_ids__annotation_types_none_returns_all(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="label",
    )
    image = create_image(session=db_session, collection_id=collection.collection_id)
    annotations = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            ),
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            ),
        ],
    )

    result = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_session,
        parent_sample_ids=[image.sample_id],
        annotation_types=None,
    )

    assert {r.sample_id for r in result} == {a.sample_id for a in annotations}


def test_get_all_by_parent_sample_ids__annotation_types_single(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="label",
    )
    image = create_image(session=db_session, collection_id=collection.collection_id)
    classification = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            ),
        ],
    )
    create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            ),
        ],
    )

    result = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_session,
        parent_sample_ids=[image.sample_id],
        annotation_types=[AnnotationType.CLASSIFICATION],
    )

    assert [r.sample_id for r in result] == [classification[0].sample_id]


def test_get_all_by_parent_sample_ids__annotation_types_multiple(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="label",
    )
    image = create_image(session=db_session, collection_id=collection.collection_id)
    classification = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            ),
        ],
    )
    object_detection = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            ),
        ],
    )
    create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.SEGMENTATION_MASK,
                segmentation_mask=[0, 1, 0, 1],
            ),
        ],
    )

    result = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_session,
        parent_sample_ids=[image.sample_id],
        annotation_types=[AnnotationType.CLASSIFICATION, AnnotationType.OBJECT_DETECTION],
    )

    assert {r.sample_id for r in result} == {
        classification[0].sample_id,
        object_detection[0].sample_id,
    }


def test_get_all_by_parent_sample_ids__annotation_types_empty_returns_empty(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="label",
    )
    image = create_image(session=db_session, collection_id=collection.collection_id)
    create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            ),
        ],
    )

    result = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_session,
        parent_sample_ids=[image.sample_id],
        annotation_types=[],
    )

    assert result == []
