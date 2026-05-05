from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import annotation_resolver, collection_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_get_sample_ids(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    sample = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/sample.png",
    )
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
    )
    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=sample.sample_id,
        annotation_label_id=label.annotation_label_id,
    )

    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    all_sample_ids = annotation_resolver.get_sample_ids(
        session=db_session,
        collection_id=annotation_collection_id,
    )
    assert all_sample_ids == {annotation.sample_id}


def test_get_sample_ids_with_label_filter(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    sample = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/sample.png",
    )
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="cat",
    )
    other_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="dog",
    )
    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=sample.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=sample.sample_id,
        annotation_label_id=other_label.annotation_label_id,
    )

    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    filtered_ids = annotation_resolver.get_sample_ids(
        session=db_session,
        collection_id=annotation_collection_id,
        filters=AnnotationsFilter(
            annotation_label_ids=[label.annotation_label_id],
        ),
    )
    assert filtered_ids == {annotation.sample_id}
