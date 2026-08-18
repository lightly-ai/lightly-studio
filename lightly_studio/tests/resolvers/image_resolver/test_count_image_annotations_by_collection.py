from __future__ import annotations

from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationCountMode
from sqlmodel import Session

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
