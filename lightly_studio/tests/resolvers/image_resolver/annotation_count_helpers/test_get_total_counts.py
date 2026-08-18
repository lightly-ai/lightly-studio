from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationCountMode
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
)


def test_get_total_counts__counts_all_annotations(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image = create_image(session=db_session, collection_id=collection_id)
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    dog_id, cat_id = dog.annotation_label_id, cat.annotation_label_id
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(sample_id=image.sample_id, annotation_label_id=dog_id),
            AnnotationDetails(sample_id=image.sample_id, annotation_label_id=dog_id),
            AnnotationDetails(sample_id=image.sample_id, annotation_label_id=cat_id),
        ],
    )

    result = annotation_count_helpers.get_total_counts(
        session=db_session,
        collection_id=collection_id,
    )

    assert result == {"cat": 1, "dog": 2}


def test_get_total_counts__filters_by_annotation_type(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image = create_image(session=db_session, collection_id=collection_id)
    scene = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="scene"
    )
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=scene.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            ),
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=dog.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            ),
        ],
    )

    result = annotation_count_helpers.get_total_counts(
        session=db_session,
        collection_id=collection_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )

    assert result == {"scene": 1}


def test_get_total_counts__samples_mode_deduplicates(db_session: Session) -> None:
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

    result = annotation_count_helpers.get_total_counts(
        session=db_session,
        collection_id=collection_id,
        count_mode=AnnotationCountMode.SAMPLES,
    )

    assert result == {"dog": 1}
