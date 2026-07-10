from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import image_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver.count_image_annotations_by_collection import (
    AnnotationCountMode,
)
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


def test_count_image_annotations_by_collection_filters_by_annotation_source(
    db_session: Session,
) -> None:
    """Selecting a subset of annotation sources counts only that source's annotations."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    image = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample1.png",
    )
    dog_label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    cat_label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )

    # Two annotation sources on the same image: "dog" from source A, "cat" from source B.
    source_a = create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
            )
        ],
        collection_name="source_a",
    )
    source_b = create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=cat_label.annotation_label_id,
            )
        ],
        collection_name="source_b",
    )
    source_a_collection_id = source_a[0].annotation_collection_id
    source_b_collection_id = source_b[0].annotation_collection_id
    assert source_a_collection_id != source_b_collection_id

    # Without a source filter both are counted.
    counts = image_resolver.count_image_annotations_by_collection(
        session=db_session,
        collection_id=collection_id,
    )
    assert {label: current for label, current, _ in counts} == {"dog": 1, "cat": 1}

    # Restricting to source A counts only its "dog"; totals stay full and "cat"
    # drops to a current count of 0.
    counts = image_resolver.count_image_annotations_by_collection(
        session=db_session,
        collection_id=collection_id,
        image_filter=ImageFilter(
            sample_filter=SampleFilter(
                annotations_filter=AnnotationsFilter(collection_ids=[source_a_collection_id])
            )
        ),
    )
    counts_dict = {label: (current, total) for label, current, total in counts}
    assert counts_dict["dog"] == (1, 1)
    assert counts_dict["cat"] == (0, 1)

    # Restricting to source B is the mirror image.
    counts = image_resolver.count_image_annotations_by_collection(
        session=db_session,
        collection_id=collection_id,
        image_filter=ImageFilter(
            sample_filter=SampleFilter(
                annotations_filter=AnnotationsFilter(collection_ids=[source_b_collection_id])
            )
        ),
    )
    counts_dict = {label: (current, total) for label, current, total in counts}
    assert counts_dict["dog"] == (0, 1)
    assert counts_dict["cat"] == (1, 1)


@pytest.fixture
def typed_collection_id(db_session: Session) -> UUID:
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

    return collection_id


@pytest.mark.parametrize(
    ("annotation_type", "expected_counts"),
    [
        (None, {"scene": (1, 1), "dog": (1, 1)}),
        (AnnotationType.CLASSIFICATION, {"scene": (1, 1)}),
        (AnnotationType.OBJECT_DETECTION, {"dog": (1, 1)}),
    ],
)
def test_count_image_annotations_by_collection_filters_by_annotation_type(
    db_session: Session,
    typed_collection_id: UUID,
    annotation_type: AnnotationType | None,
    expected_counts: dict[str, tuple[int, int]],
) -> None:
    counts = image_resolver.count_image_annotations_by_collection(
        session=db_session,
        collection_id=typed_collection_id,
        annotation_type=annotation_type,
    )

    counts_dict = {label: (current, total) for label, current, total in counts}
    assert counts_dict == expected_counts


def test_count_image_annotations_by_collection__samples_mode(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    image_a = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/image_a.png",
    )
    image_b = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/image_b.png",
    )

    car_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="car",
    )
    person_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="person",
    )

    # image_a: car, car, person — image_b: car
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image_a.sample_id,
                annotation_label_id=car_label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image_a.sample_id,
                annotation_label_id=car_label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image_a.sample_id,
                annotation_label_id=person_label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image_b.sample_id,
                annotation_label_id=car_label.annotation_label_id,
            ),
        ],
    )

    counts = image_resolver.count_image_annotations_by_collection(
        session=db_session,
        collection_id=collection_id,
        count_mode=AnnotationCountMode.SAMPLES,
    )

    counts_dict = {label: total for label, _, total in counts}
    assert counts_dict["car"] == 2
    assert counts_dict["person"] == 1


def test_count_image_annotations_by_collection__samples_mode_with_filter(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    image_a = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/image_a.png",
    )
    image_b = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/image_b.png",
    )

    car_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="car",
    )
    person_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="person",
    )

    # image_a: car, car, person — image_b: car
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image_a.sample_id,
                annotation_label_id=car_label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image_a.sample_id,
                annotation_label_id=car_label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image_a.sample_id,
                annotation_label_id=person_label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image_b.sample_id,
                annotation_label_id=car_label.annotation_label_id,
            ),
        ],
    )

    # Filter to only images that have a person annotation — only image_a matches.
    counts = image_resolver.count_image_annotations_by_collection(
        session=db_session,
        collection_id=collection_id,
        image_filter=ImageFilter(
            sample_filter=SampleFilter(
                annotations_filter=AnnotationsFilter(
                    annotation_label_ids=[person_label.annotation_label_id]
                )
            )
        ),
        count_mode=AnnotationCountMode.SAMPLES,
    )

    counts_dict = {label: (current, total) for label, current, total in counts}
    # current: only image_a is in filter — 1 distinct sample for car, 1 for person
    assert counts_dict["car"] == (1, 2)
    assert counts_dict["person"] == (1, 1)
