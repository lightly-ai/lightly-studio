from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import (
    create_annotation_label,
    create_collection,
    create_image,
)


@pytest.fixture
def collection_with_annotations(
    db_session: Session,
) -> CollectionTable:
    """Creates a collection with samples, labels and annotations.

    Note: Confidence denominators are powers of 2 to allow precise float comparisons in tests.
    """
    collection = create_collection(session=db_session, collection_name="test_collection")
    s1 = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="img1",
        width=100,
        height=100,
    )
    s2 = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="img2",
        width=200,
        height=200,
    )
    create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="img3",
        width=300,
        height=300,
    )
    dog_label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="dog"
    )
    cat_label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="zebra"
    )

    # Create annotations:
    # - s1: dog, cat
    # - s2: dog
    # - s3: (none)
    annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        annotations=[
            AnnotationCreate(
                parent_sample_id=s1.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                confidence=None,
                x=10,
                y=10,
                width=10,
                height=10,
            ),
            AnnotationCreate(
                parent_sample_id=s1.sample_id,
                annotation_label_id=cat_label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                confidence=2 / 8,
                x=20,
                y=20,
                width=20,
                height=20,
            ),
            AnnotationCreate(
                parent_sample_id=s2.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                confidence=3 / 8,
                x=30,
                y=30,
                width=30,
                height=30,
            ),
        ],
    )
    return collection
