from __future__ import annotations

from dataclasses import dataclass

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import image_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
)


@dataclass
class _TestData:
    collection: CollectionTable
    dog_label: AnnotationLabelTable
    cat_label: AnnotationLabelTable


@pytest.fixture
def test_data(db_session: Session) -> _TestData:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    image1 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample1.png",
    )
    image2 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample2.png",
    )

    dog_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="dog",
    )
    cat_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="cat",
    )

    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image1.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image2.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image1.sample_id,
                annotation_label_id=cat_label.annotation_label_id,
            ),
        ],
    )

    return _TestData(collection=collection, dog_label=dog_label, cat_label=cat_label)


def test_count_image_annotations_by_collection(db_session: Session, test_data: _TestData) -> None:
    annotation_counts = image_resolver.count_image_annotations_by_collection(
        session=db_session,
        collection_id=test_data.collection.collection_id,
    )

    assert len(annotation_counts) == 2
    annotation_dict = {label: current for (label, current, _) in annotation_counts}
    assert annotation_dict["dog"] == 2
    assert annotation_dict["cat"] == 1


def test_count_image_annotations_by_collection_with_filtering(
    db_session: Session,
    test_data: _TestData,
) -> None:
    collection_id = test_data.collection.collection_id

    counts = image_resolver.count_image_annotations_by_collection(
        session=db_session,
        collection_id=collection_id,
    )
    counts_dict = {label: (current, total) for label, current, total in counts}
    assert counts_dict["dog"] == (2, 2)
    assert counts_dict["cat"] == (1, 1)

    filtered_counts = image_resolver.count_image_annotations_by_collection(
        session=db_session,
        collection_id=collection_id,
        image_filter=ImageFilter(
            sample_filter=SampleFilter(
                annotations_filter=AnnotationsFilter(
                    annotation_label_ids=[test_data.dog_label.annotation_label_id]
                )
            )
        ),
    )
    filtered_dict = {label: (current, total) for label, current, total in filtered_counts}
    assert filtered_dict["dog"] == (2, 2)
    assert filtered_dict["cat"] == (1, 1)

    filtered_counts = image_resolver.count_image_annotations_by_collection(
        session=db_session,
        collection_id=collection_id,
        image_filter=ImageFilter(
            sample_filter=SampleFilter(
                annotations_filter=AnnotationsFilter(
                    annotation_label_ids=[test_data.cat_label.annotation_label_id]
                )
            )
        ),
    )
    filtered_dict = {label: (current, total) for label, current, total in filtered_counts}
    assert filtered_dict["dog"] == (1, 2)
    assert filtered_dict["cat"] == (1, 1)


def test_count_image_annotations_by_collection_filters_by_annotation_type(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    image = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample1.png",
    )

    classification_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="scene",
    )
    detection_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="dog",
    )

    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=classification_label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            ),
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=detection_label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            ),
        ],
    )

    # Without the filter both types are counted.
    all_counts = image_resolver.count_image_annotations_by_collection(
        session=db_session,
        collection_id=collection_id,
    )
    all_dict = {label: (current, total) for label, current, total in all_counts}
    assert all_dict == {"scene": (1, 1), "dog": (1, 1)}

    # Classification only isolates the classification label.
    classification_counts = image_resolver.count_image_annotations_by_collection(
        session=db_session,
        collection_id=collection_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )
    classification_dict = {
        label: (current, total) for label, current, total in classification_counts
    }
    assert classification_dict == {"scene": (1, 1)}

    # Object detection only isolates the detection label.
    detection_counts = image_resolver.count_image_annotations_by_collection(
        session=db_session,
        collection_id=collection_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    detection_dict = {label: (current, total) for label, current, total in detection_counts}
    assert detection_dict == {"dog": (1, 1)}
