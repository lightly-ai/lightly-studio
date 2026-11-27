"""Tests for annotation_label_resolver - get_annotation_counts functionality."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import annotation_label_resolver
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
)


def test_get_annotation_counts(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    image_id = create_image(session=db_session, collection_id=collection_id).sample_id
    cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    for _ in range(2):
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=image_id,
            annotation_label_id=cat.annotation_label_id,
        )
    # A label of another dataset is not counted.
    other_collection_id = create_collection(
        session=db_session, collection_name="other"
    ).collection_id
    create_annotation_label(
        session=db_session, root_collection_id=other_collection_id, label_name="bird"
    )

    counts = annotation_label_resolver.get_annotation_counts(
        session=db_session, dataset_id=cat.dataset_id
    )

    assert counts == {cat.annotation_label_id: 2, dog.annotation_label_id: 0}


def test_get_annotation_counts__counts_all_collections(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    image_id = create_image(session=db_session, collection_id=collection_id).sample_id
    cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    for collection_name in ("ground_truth", "predictions"):
        create_annotations(
            session=db_session,
            collection_id=collection_id,
            annotations=[
                AnnotationDetails(sample_id=image_id, annotation_label_id=cat.annotation_label_id)
            ],
            collection_name=collection_name,
        )

    counts = annotation_label_resolver.get_annotation_counts(
        session=db_session, dataset_id=cat.dataset_id
    )

    assert counts == {cat.annotation_label_id: 2}
