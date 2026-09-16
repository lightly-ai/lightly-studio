from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.resolvers import image_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationCountMode
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
)


def test_count_image_annotations_by_type(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/to/sample1.png"
    )
    label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            ),
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

    counts = image_resolver.count_image_annotations_by_type(
        session=db_session, collection_id=collection_id
    )

    assert counts == [
        (AnnotationType.CLASSIFICATION, 1, 1),
        (AnnotationType.OBJECT_DETECTION, 2, 2),
    ]


def test_count_image_annotations_by_type__filter_narrows_current_count(
    db_session: Session,
) -> None:
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
                sample_id=image1.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            ),
            AnnotationDetails(
                sample_id=image2.sample_id,
                annotation_label_id=cat_label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            ),
            AnnotationDetails(
                sample_id=image2.sample_id,
                annotation_label_id=cat_label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            ),
        ],
    )

    counts = image_resolver.count_image_annotations_by_type(
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

    # Only image1 matches the dog filter, so its single detection is the current count while
    # both types keep their unfiltered totals.
    assert counts == [
        (AnnotationType.CLASSIFICATION, 0, 1),
        (AnnotationType.OBJECT_DETECTION, 1, 2),
    ]


def test_count_image_annotations_by_type__samples_count_mode(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/to/sample1.png"
    )
    label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            ),
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            ),
        ],
    )

    counts = image_resolver.count_image_annotations_by_type(
        session=db_session,
        collection_id=collection_id,
        count_mode=AnnotationCountMode.SAMPLES,
    )

    # Two detections on one image count as a single annotated sample.
    assert counts == [(AnnotationType.OBJECT_DETECTION, 1, 1)]
