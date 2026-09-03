"""Tests for the get_parent_sample_ids_with_label resolver."""

from __future__ import annotations

import uuid

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_get_parent_sample_ids_with_label(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    labeled = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="a.png"
    )
    unlabeled = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="b.png"
    )
    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=labeled.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
        annotation_data={},
    )

    result = annotation_resolver.get_parent_sample_ids_with_label(
        session=db_session,
        parent_sample_ids=[labeled.sample_id, unlabeled.sample_id],
        annotation_label_id=label.annotation_label_id,
        annotation_collection_id=annotation.sample.collection_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )

    assert result == {labeled.sample_id}


def test_get_parent_sample_ids_with_label__filters_by_label(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    cat = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="dog"
    )
    image = create_image(session=db_session, collection_id=collection.collection_id)
    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=cat.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
        annotation_data={},
    )

    result = annotation_resolver.get_parent_sample_ids_with_label(
        session=db_session,
        parent_sample_ids=[image.sample_id],
        annotation_label_id=dog.annotation_label_id,
        annotation_collection_id=annotation.sample.collection_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )

    assert result == set()


def test_get_parent_sample_ids_with_label__filters_by_annotation_collection(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    in_ground_truth = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="a.png"
    )
    in_predictions = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="b.png"
    )
    ground_truth_annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=in_ground_truth.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
        annotation_data={},
        annotation_collection_name="ground_truth",
    )
    create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=in_predictions.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
        annotation_data={},
        annotation_collection_name="predictions",
    )

    result = annotation_resolver.get_parent_sample_ids_with_label(
        session=db_session,
        parent_sample_ids=[in_ground_truth.sample_id, in_predictions.sample_id],
        annotation_label_id=label.annotation_label_id,
        annotation_collection_id=ground_truth_annotation.sample.collection_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )

    assert result == {in_ground_truth.sample_id}


def test_get_parent_sample_ids_with_label__filters_by_annotation_type(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="car"
    )
    image = create_image(session=db_session, collection_id=collection.collection_id)
    detection = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )

    result = annotation_resolver.get_parent_sample_ids_with_label(
        session=db_session,
        parent_sample_ids=[image.sample_id],
        annotation_label_id=label.annotation_label_id,
        annotation_collection_id=detection.sample.collection_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )

    assert result == set()


def test_get_parent_sample_ids_with_label__empty_parent_sample_ids(db_session: Session) -> None:
    result = annotation_resolver.get_parent_sample_ids_with_label(
        session=db_session,
        parent_sample_ids=[],
        annotation_label_id=uuid.uuid4(),
        annotation_collection_id=uuid.uuid4(),
        annotation_type=AnnotationType.CLASSIFICATION,
    )

    assert result == set()
