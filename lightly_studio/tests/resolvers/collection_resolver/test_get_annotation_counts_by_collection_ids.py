from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
)


def test_get_annotation_counts_by_collection_ids(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    details = AnnotationDetails(
        sample_id=image.sample_id, annotation_label_id=label.annotation_label_id
    )
    (gt,) = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[details],
        collection_name="ground_truth",
    )
    pred, _ = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[details, details],
        collection_name="predictions",
    )
    empty = create_collection(
        session=db_session,
        collection_name="empty",
        parent_collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    counts = collection_resolver.get_annotation_counts_by_collection_ids(
        session=db_session,
        collection_ids=[
            gt.annotation_collection_id,
            pred.annotation_collection_id,
            empty.collection_id,
        ],
    )

    assert counts == {gt.annotation_collection_id: 1, pred.annotation_collection_id: 2}


def test_get_annotation_counts_by_collection_ids__only_given_ids(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    details = AnnotationDetails(
        sample_id=image.sample_id, annotation_label_id=label.annotation_label_id
    )
    (gt,) = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[details],
        collection_name="ground_truth",
    )
    create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[details],
        collection_name="predictions",
    )

    counts = collection_resolver.get_annotation_counts_by_collection_ids(
        session=db_session, collection_ids=[gt.annotation_collection_id]
    )

    assert counts == {gt.annotation_collection_id: 1}


def test_get_annotation_counts_by_collection_ids__empty(db_session: Session) -> None:
    assert (
        collection_resolver.get_annotation_counts_by_collection_ids(
            session=db_session, collection_ids=[]
        )
        == {}
    )
