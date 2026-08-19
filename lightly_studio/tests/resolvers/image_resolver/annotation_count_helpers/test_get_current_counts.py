from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
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


def test_get_current_counts__no_filter_returns_all(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image = create_image(session=db_session, collection_id=collection_id)
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    dog_id = dog.annotation_label_id
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(sample_id=image.sample_id, annotation_label_id=dog_id),
            AnnotationDetails(sample_id=image.sample_id, annotation_label_id=dog_id),
        ],
    )

    result = annotation_count_helpers.get_current_counts(
        session=db_session,
        collection_id=collection_id,
        image_filter=None,
    )

    assert result == {"dog": 2}


def test_get_current_counts__filter_reduces_count(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image_a = create_image(session=db_session, collection_id=collection_id, file_path_abs="a.png")
    image_b = create_image(session=db_session, collection_id=collection_id, file_path_abs="b.png")
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    dog_id, cat_id = dog.annotation_label_id, cat.annotation_label_id
    source = create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(sample_id=image_a.sample_id, annotation_label_id=dog_id),
            AnnotationDetails(sample_id=image_b.sample_id, annotation_label_id=dog_id),
            AnnotationDetails(sample_id=image_a.sample_id, annotation_label_id=cat_id),
        ],
    )
    source_id = source[0].annotation_collection_id
    # Filter to only images annotated with cat — only image_a matches.
    image_filter = ImageFilter(
        sample_filter=SampleFilter(
            annotations_filter=AnnotationsFilter(
                annotation_label_ids=[cat_id],
                collection_ids=[source_id],
            )
        )
    )

    result = annotation_count_helpers.get_current_counts(
        session=db_session,
        collection_id=collection_id,
        image_filter=image_filter,
        annotation_collection_ids=[source_id],
    )

    assert result == {"cat": 1, "dog": 1}


def test_get_current_counts__samples_mode(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image = create_image(session=db_session, collection_id=collection_id)
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    dog_id = dog.annotation_label_id
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(sample_id=image.sample_id, annotation_label_id=dog_id),
            AnnotationDetails(sample_id=image.sample_id, annotation_label_id=dog_id),
        ],
    )

    result = annotation_count_helpers.get_current_counts(
        session=db_session,
        collection_id=collection_id,
        image_filter=None,
        count_mode=AnnotationCountMode.SAMPLES,
    )

    assert result == {"dog": 1}


def test_get_current_counts__annotation_type_filters_results(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image = create_image(session=db_session, collection_id=collection_id)
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    dog_id = dog.annotation_label_id
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=dog_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            ),
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=dog_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            ),
        ],
    )

    result = annotation_count_helpers.get_current_counts(
        session=db_session,
        collection_id=collection_id,
        image_filter=None,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )

    assert result == {"dog": 1}


def test_get_current_counts__annotation_collection_ids_excludes_other_sources(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image = create_image(session=db_session, collection_id=collection_id)
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    source_a = create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id, annotation_label_id=dog.annotation_label_id
            )
        ],
        collection_name="source-a",
    )
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id, annotation_label_id=cat.annotation_label_id
            )
        ],
        collection_name="source-b",
    )

    result = annotation_count_helpers.get_current_counts(
        session=db_session,
        collection_id=collection_id,
        image_filter=None,
        annotation_collection_ids=[source_a[0].annotation_collection_id],
    )

    assert result == {"dog": 1}
