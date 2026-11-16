from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.embedding_region import EmbeddingRegion, Point2D
from lightly_studio.resolvers import image_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationCountMode
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
)
from tests.resolvers.image_resolver import annotation_count_cases
from tests.resolvers.image_resolver.annotation_count_cases import BuildFilter


def test_count_image_annotations_by_collection_with_filtering(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image1 = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/to/sample1.png"
    )
    image2 = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/to/sample2.png"
    )
    dog_label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    cat_label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image1.sample_id, annotation_label_id=dog_label.annotation_label_id
            ),
            AnnotationDetails(
                sample_id=image2.sample_id, annotation_label_id=dog_label.annotation_label_id
            ),
            AnnotationDetails(
                sample_id=image1.sample_id, annotation_label_id=cat_label.annotation_label_id
            ),
        ],
    )

    # Filter to images with dog — both images match, totals unchanged.
    counts = image_resolver.count_image_annotations_by_collection(
        session=db_session,
        collection_id=collection_id,
        image_filter=ImageFilter(
            sample_filter=SampleFilter(
                annotations_filter=AnnotationsFilter(
                    annotation_label_ids=[dog_label.annotation_label_id]
                )
            )
        ),
    )
    assert {label: (current, total) for label, current, total in counts} == {
        "dog": (2, 2),
        "cat": (1, 1),
    }

    # Filter to images with cat — only image1 matches, dog current drops to 1.
    counts = image_resolver.count_image_annotations_by_collection(
        session=db_session,
        collection_id=collection_id,
        image_filter=ImageFilter(
            sample_filter=SampleFilter(
                annotations_filter=AnnotationsFilter(
                    annotation_label_ids=[cat_label.annotation_label_id]
                )
            )
        ),
    )
    assert {label: (current, total) for label, current, total in counts} == {
        "dog": (1, 2),
        "cat": (1, 1),
    }


def test_count_image_annotations_by_collection_total_excludes_other_sources(
    db_session: Session,
) -> None:
    """A shared label's total is scoped to the selected source, not summed across all."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    shared_label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="shared"
    )
    image_a = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/to/source_a.png"
    )
    image_b = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/to/source_b.png"
    )
    source_a = create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image_a.sample_id, annotation_label_id=shared_label.annotation_label_id
            )
        ],
        collection_name="source_a",
    )
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image_b.sample_id, annotation_label_id=shared_label.annotation_label_id
            )
        ],
        collection_name="source_b",
    )

    # Restricting to source A must report "1 of 1", not "1 of 2".
    counts = image_resolver.count_image_annotations_by_collection(
        session=db_session,
        collection_id=collection_id,
        image_filter=ImageFilter(
            sample_filter=SampleFilter(
                annotations_filter=AnnotationsFilter(
                    collection_ids=[source_a[0].annotation_collection_id]
                )
            )
        ),
    )
    assert {label: (current, total) for label, current, total in counts} == {"shared": (1, 1)}


def test_count_image_annotations_by_collection__samples_mode_with_filter(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image_a = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/to/image_a.png"
    )
    image_b = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/to/image_b.png"
    )
    car_label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="car"
    )
    person_label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="person"
    )
    # image_a: car, car, person — image_b: car
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image_a.sample_id, annotation_label_id=car_label.annotation_label_id
            ),
            AnnotationDetails(
                sample_id=image_a.sample_id, annotation_label_id=car_label.annotation_label_id
            ),
            AnnotationDetails(
                sample_id=image_a.sample_id, annotation_label_id=person_label.annotation_label_id
            ),
            AnnotationDetails(
                sample_id=image_b.sample_id, annotation_label_id=car_label.annotation_label_id
            ),
        ],
    )

    # Filter to images with person — only image_a matches; car: 1 current, 2 total.
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
    assert {label: (current, total) for label, current, total in counts} == {
        "car": (1, 2),
        "person": (1, 1),
    }


# The (label, current, total) counts of each case, worked out by hand from create_count_data.
# Source A: car and person on image 1, car on image 2, car classification on image 3.
# Source B: person on image 2, car on image 3. Widths: 100, 200, 300.
# Image tag 1 is on image 1. The annotation tag is on the source A car on image 1.
EXPECTED_COUNTS = {
    "no_filter": [("car", 4, 4), ("person", 2, 2)],
    "empty_image_filter": [("car", 4, 4), ("person", 2, 2)],
    "sources_only": [("car", 3, 3), ("person", 1, 1)],
    "empty_source_list": [("car", 4, 4), ("person", 2, 2)],
    "empty_annotations_filter": [("car", 4, 4), ("person", 2, 2)],
    "sources_and_image_tag": [("car", 1, 3), ("person", 1, 1)],
    "sources_and_width": [("car", 2, 3), ("person", 0, 1)],
    "sources_and_image_region": [("car", 1, 3), ("person", 1, 1)],
    "sources_and_label": [("car", 3, 3), ("person", 1, 1)],
    # Images 1 and 2 have an object detection in source A; image 3 has a classification only.
    "sources_and_type": [("car", 2, 3), ("person", 1, 1)],
    "sources_and_annotation_tag": [("car", 1, 3), ("person", 1, 1)],
    "sources_and_annotation_ids": [("car", 1, 3), ("person", 1, 1)],
    "sources_and_empty_annotation_region": [("car", 0, 3), ("person", 0, 1)],
    "sources_and_annotation_region": [("car", 1, 3), ("person", 1, 1)],
}


@pytest.mark.parametrize(
    ("case_id", "expected"),
    [pytest.param(case_id, expected, id=case_id) for case_id, expected in EXPECTED_COUNTS.items()],
)
def test_count_image_annotations_by_collection__counts_by_hand(
    db_session: Session, case_id: str, expected: list[tuple[str, int, int]]
) -> None:
    data = annotation_count_cases.create_count_data(session=db_session)
    build_filter = annotation_count_cases.BUILD_FILTER_BY_ID[case_id]

    counts = image_resolver.count_image_annotations_by_collection(
        session=db_session, collection_id=data.collection_id, image_filter=build_filter(data)
    )

    assert counts == expected


@pytest.mark.parametrize("count_mode", [AnnotationCountMode.OBJECTS, AnnotationCountMode.SAMPLES])
@pytest.mark.parametrize("annotation_type", [None, AnnotationType.OBJECT_DETECTION])
@pytest.mark.parametrize("build_filter", annotation_count_cases.BUILD_FILTERS)
def test_count_image_annotations_by_collection__matches_unstripped_counts(
    db_session: Session,
    build_filter: BuildFilter,
    annotation_type: AnnotationType | None,
    count_mode: AnnotationCountMode,
) -> None:
    data = annotation_count_cases.create_count_data(session=db_session)
    # The helpers on an unstripped filter still add the parent IN.
    expected_filter = build_filter(data)
    annotation_collection_ids = annotation_count_helpers.get_annotation_collection_ids(
        image_filter=expected_filter
    )
    total_counts = annotation_count_helpers.get_total_counts(
        session=db_session,
        collection_id=data.collection_id,
        annotation_type=annotation_type,
        count_mode=count_mode,
        annotation_collection_ids=annotation_collection_ids,
    )
    current_counts = annotation_count_helpers.get_current_counts(
        session=db_session,
        collection_id=data.collection_id,
        image_filter=expected_filter,
        annotation_type=annotation_type,
        annotation_collection_ids=annotation_collection_ids,
        count_mode=count_mode,
    )

    counts = image_resolver.count_image_annotations_by_collection(
        session=db_session,
        collection_id=data.collection_id,
        image_filter=build_filter(data),
        annotation_type=annotation_type,
        count_mode=count_mode,
    )

    assert total_counts
    assert counts == [
        (label, current_counts.get(label, 0), total) for label, total in total_counts.items()
    ]


@pytest.mark.parametrize(("group", "build_filter"), annotation_count_cases.CASES)
def test_count_image_annotations_by_collection__statements(
    db_session: Session, group: str, build_filter: BuildFilter
) -> None:
    data = annotation_count_cases.create_count_data(session=db_session)
    image_filter = build_filter(data)
    sample_filter = image_filter.sample_filter if image_filter is not None else None
    annotations_filter = sample_filter.annotations_filter if sample_filter is not None else None
    collection_ids = annotations_filter.collection_ids if annotations_filter is not None else None

    with annotation_count_cases.record_statements(session=db_session) as statements:
        image_resolver.count_image_annotations_by_collection(
            session=db_session, collection_id=data.collection_id, image_filter=image_filter
        )

    # Skip cases run the total only. The others also run the current.
    assert len(statements) == (1 if group == "skip" else 2)
    has_parent_in = any(annotation_count_cases.PARENT_IN_MARKER in s for s in statements)
    assert has_parent_in == (group == "keep")
    # The caller's filter keeps its source selection.
    if annotations_filter is not None:
        assert annotations_filter.collection_ids == collection_ids


def test_count_image_annotations_by_collection__sources_with_embedding_region(
    db_session: Session,
) -> None:
    collection_id, images = annotation_count_cases.create_images_in_plot(
        session=db_session, coordinates=[(1.0, 1.0), (5.0, 5.0), (100.0, 100.0)]
    )
    car = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="car"
    )
    source = create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id, annotation_label_id=car.annotation_label_id
            )
            for image in images
        ],
        collection_name="source",
    )

    # The square encloses the first two plot points, but not (100, 100).
    region = EmbeddingRegion(
        polygon=[Point2D(x=0, y=0), Point2D(x=10, y=0), Point2D(x=10, y=10), Point2D(x=0, y=10)]
    )
    counts = image_resolver.count_image_annotations_by_collection(
        session=db_session,
        collection_id=collection_id,
        image_filter=ImageFilter(
            sample_filter=SampleFilter(
                embedding_region=region,
                annotations_filter=AnnotationsFilter(
                    collection_ids=[source[0].annotation_collection_id]
                ),
            )
        ),
    )

    assert counts == [("car", 2, 3)]
