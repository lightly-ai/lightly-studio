from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_get_annotation_types_by_collection_ids__distinct_and_sorted(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    sample = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id
    )

    # Two object-detection annotations (duplicate type) plus one classification.
    for annotation_type in (
        AnnotationType.OBJECT_DETECTION,
        AnnotationType.OBJECT_DETECTION,
        AnnotationType.CLASSIFICATION,
    ):
        create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=sample.sample_id,
            annotation_label_id=label.annotation_label_id,
            annotation_type=annotation_type,
        )

    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    result = collection_resolver.get_annotation_types_by_collection_ids(
        session=db_session,
        collection_ids=[annotation_collection_id],
    )

    # Distinct values, sorted alphabetically.
    assert result == {annotation_collection_id: ["classification", "object_detection"]}


def test_get_annotation_types_by_collection_ids__empty_input(db_session: Session) -> None:
    assert (
        collection_resolver.get_annotation_types_by_collection_ids(
            session=db_session, collection_ids=[]
        )
        == {}
    )


def test_get_annotation_types_by_collection_ids__omits_collections_without_annotations(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    empty_annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    result = collection_resolver.get_annotation_types_by_collection_ids(
        session=db_session,
        collection_ids=[empty_annotation_collection_id],
    )

    assert result == {}
