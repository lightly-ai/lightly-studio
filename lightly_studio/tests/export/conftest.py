from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.dataset import DatasetTable
from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import (
    create_annotation_label,
    create_dataset,
    create_image,
)


@pytest.fixture
def dataset_with_annotations(
    db_session: Session,
) -> DatasetTable:
    """Creates a dataset with samples, labels and annotations.

    Note: Confidence denominators are powers of 2 to allow precise float comparisons in tests.
    """
    dataset = create_dataset(session=db_session, dataset_name="test_dataset")
    s1 = create_image(
        session=db_session,
        dataset_id=dataset.dataset_id,
        file_path_abs="img1",
        width=100,
        height=100,
    )
    s2 = create_image(
        session=db_session,
        dataset_id=dataset.dataset_id,
        file_path_abs="img2",
        width=200,
        height=200,
    )
    create_image(
        session=db_session,
        dataset_id=dataset.dataset_id,
        file_path_abs="img3",
        width=300,
        height=300,
    )
    dog_label = create_annotation_label(session=db_session, annotation_label_name="dog")
    cat_label = create_annotation_label(session=db_session, annotation_label_name="cat")
    create_annotation_label(session=db_session, annotation_label_name="zebra")

    # Create annotations:
    # - s1: dog, cat
    # - s2: dog
    # - s3: (none)
    annotation_resolver.create_many(
        session=db_session,
        annotations=[
            AnnotationCreate(
                sample_id=s1.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                dataset_id=dataset.dataset_id,
                confidence=None,
                x=10,
                y=10,
                width=10,
                height=10,
            ),
            AnnotationCreate(
                sample_id=s1.sample_id,
                annotation_label_id=cat_label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                dataset_id=dataset.dataset_id,
                confidence=2 / 8,
                x=20,
                y=20,
                width=20,
                height=20,
            ),
            AnnotationCreate(
                sample_id=s2.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                dataset_id=dataset.dataset_id,
                confidence=3 / 8,
                x=30,
                y=30,
                width=30,
                height=30,
            ),
        ],
    )
    return dataset
