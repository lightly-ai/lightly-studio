from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import annotation_resolver, collection_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
)


def test_get_unembedded_annotation_ids__returns_annotations_without_embeddings(
    db_session: Session,
) -> None:
    """Only object-detection annotations lacking an embedding for the model are returned."""
    collection = create_collection(session=db_session)
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    embedded_annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    other_image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/other.png",
    )
    unembedded_annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=other_image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    embedding_model = create_embedding_model(
        session=db_session, collection_id=annotation_collection_id
    )
    create_sample_embedding(
        session=db_session,
        sample_id=embedded_annotation.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.1, 0.2, 0.3],
    )

    unembedded_ids = annotation_resolver.get_unembedded_annotation_ids(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    assert unembedded_ids == [unembedded_annotation.sample_id]


def test_get_unembedded_annotation_ids__orders_by_image_path(
    db_session: Session,
) -> None:
    """Results are ordered by source image path so annotations on the same image stay adjacent."""
    collection = create_collection(session=db_session)
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    image_b = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/b.png",
    )
    image_a = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/a.png",
    )
    annotation_b = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image_b.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    annotation_a = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image_a.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    embedding_model = create_embedding_model(
        session=db_session, collection_id=annotation_collection_id
    )

    unembedded_ids = annotation_resolver.get_unembedded_annotation_ids(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    assert unembedded_ids == [annotation_a.sample_id, annotation_b.sample_id]
