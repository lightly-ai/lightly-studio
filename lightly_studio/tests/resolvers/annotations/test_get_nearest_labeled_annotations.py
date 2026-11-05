from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
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


def test_get_nearest_labeled_annotations__orders_by_similarity_and_limits(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    annotation_collection_id = _get_annotation_collection_id(
        session=db_session, root_collection_id=collection.collection_id
    )
    cat = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="dog"
    )
    model = create_embedding_model(session=db_session, collection_id=annotation_collection_id)
    query = _create_annotation(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_id=cat.annotation_label_id,
    )
    for label_id, embedding in [
        (cat.annotation_label_id, [1.0, 0.0, 0.0]),
        (dog.annotation_label_id, [0.9, 0.1, 0.0]),
        (cat.annotation_label_id, [0.0, 1.0, 0.0]),
    ]:
        annotation = _create_annotation(
            session=db_session, root_collection_id=collection.collection_id, label_id=label_id
        )
        create_sample_embedding(
            session=db_session,
            sample_id=annotation.sample_id,
            embedding_model_id=model.embedding_model_id,
            embedding=embedding,
        )

    neighbours = annotation_resolver.get_nearest_labeled_annotations(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        embedding_model_id=model.embedding_model_id,
        query_embedding=[1.0, 0.0, 0.0],
        exclude_annotation_id=query.sample_id,
        limit=2,
    )

    assert [n.annotation_label_id for n in neighbours] == [
        cat.annotation_label_id,
        dog.annotation_label_id,
    ]
    assert neighbours[0].similarity == pytest.approx(1.0)
    assert neighbours[1].similarity == pytest.approx(0.9 / (0.81 + 0.01) ** 0.5)


def test_get_nearest_labeled_annotations__excludes_query_annotation(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    annotation_collection_id = _get_annotation_collection_id(
        session=db_session, root_collection_id=collection.collection_id
    )
    cat = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="dog"
    )
    model = create_embedding_model(session=db_session, collection_id=annotation_collection_id)
    query = _create_annotation(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_id=cat.annotation_label_id,
    )
    create_sample_embedding(
        session=db_session,
        sample_id=query.sample_id,
        embedding_model_id=model.embedding_model_id,
        embedding=[1.0, 0.0, 0.0],
    )
    other = _create_annotation(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_id=dog.annotation_label_id,
    )
    create_sample_embedding(
        session=db_session,
        sample_id=other.sample_id,
        embedding_model_id=model.embedding_model_id,
        embedding=[0.0, 1.0, 0.0],
    )

    neighbours = annotation_resolver.get_nearest_labeled_annotations(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        embedding_model_id=model.embedding_model_id,
        query_embedding=[1.0, 0.0, 0.0],
        exclude_annotation_id=query.sample_id,
        limit=10,
    )

    assert [n.annotation_label_id for n in neighbours] == [dog.annotation_label_id]


def test_get_nearest_labeled_annotations__ignores_other_model_and_other_collection(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    annotation_collection_id = _get_annotation_collection_id(
        session=db_session, root_collection_id=collection.collection_id
    )
    cat = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="dog"
    )
    model = create_embedding_model(
        session=db_session, collection_id=annotation_collection_id, embedding_model_name="model"
    )
    other_model = create_embedding_model(
        session=db_session,
        collection_id=annotation_collection_id,
        embedding_model_name="other_model",
    )
    query = _create_annotation(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_id=cat.annotation_label_id,
    )
    far = _create_annotation(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_id=cat.annotation_label_id,
    )
    create_sample_embedding(
        session=db_session,
        sample_id=far.sample_id,
        embedding_model_id=model.embedding_model_id,
        embedding=[0.0, 1.0, 0.0],
    )
    # Closer to the query, but stored for another model.
    create_sample_embedding(
        session=db_session,
        sample_id=far.sample_id,
        embedding_model_id=other_model.embedding_model_id,
        embedding=[1.0, 0.0, 0.0],
    )
    # Closer to the query, but in another annotation collection.
    other_collection_annotation = _create_annotation(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_id=dog.annotation_label_id,
        annotation_collection_name="other_source",
    )
    create_sample_embedding(
        session=db_session,
        sample_id=other_collection_annotation.sample_id,
        embedding_model_id=model.embedding_model_id,
        embedding=[1.0, 0.0, 0.0],
    )

    neighbours = annotation_resolver.get_nearest_labeled_annotations(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        embedding_model_id=model.embedding_model_id,
        query_embedding=[1.0, 0.0, 0.0],
        exclude_annotation_id=query.sample_id,
        limit=10,
    )

    assert len(neighbours) == 1
    assert neighbours[0].annotation_label_id == cat.annotation_label_id
    assert neighbours[0].similarity == pytest.approx(0.0)


def _get_annotation_collection_id(session: Session, root_collection_id: UUID) -> UUID:
    return collection_resolver.get_or_create_child_collection(
        session=session,
        collection_id=root_collection_id,
        sample_type=SampleType.ANNOTATION,
    )


def _create_annotation(
    session: Session,
    root_collection_id: UUID,
    label_id: UUID,
    annotation_collection_name: str | None = None,
) -> AnnotationBaseTable:
    image = create_image(
        session=session,
        collection_id=root_collection_id,
        file_path_abs=f"/path/to/{uuid4()}.png",
    )
    return create_annotation(
        session=session,
        collection_id=root_collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label_id,
        annotation_collection_name=annotation_collection_name,
    )
