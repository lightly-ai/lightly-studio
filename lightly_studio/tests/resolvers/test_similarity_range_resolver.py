from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.resolvers import similarity_range_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
)


def test_get_similarity_range(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    model_id = create_embedding_model(
        session=db_session, collection_id=collection_id, embedding_dimension=2, set_as_default=True
    ).embedding_model_id
    # Similarities to [1, 0]: 1.0, ~0.707 and 0.0.
    for index, embedding in enumerate([[1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]):
        image = create_image(
            session=db_session, collection_id=collection_id, file_path_abs=f"{index}.png"
        )
        create_sample_embedding(
            session=db_session,
            sample_id=image.sample_id,
            embedding_model_id=model_id,
            embedding=embedding,
        )

    similarity_range = similarity_range_resolver.get_similarity_range(
        session=db_session, collection_id=collection_id, text_embedding=[1.0, 0.0]
    )

    assert similarity_range is not None
    assert similarity_range.min == pytest.approx(0.0, abs=1e-6)
    assert similarity_range.max == pytest.approx(1.0, abs=1e-6)


def test_get_similarity_range__ignores_other_models_and_collections(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    model_id = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="model_a",
        embedding_dimension=2,
        set_as_default=True,
    ).embedding_model_id
    other_model_id = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="model_b",
        embedding_dimension=2,
    ).embedding_model_id
    image = create_image(session=db_session, collection_id=collection_id, file_path_abs="a.png")
    create_sample_embedding(
        session=db_session,
        sample_id=image.sample_id,
        embedding_model_id=model_id,
        embedding=[1.0, 1.0],
    )
    create_sample_embedding(
        session=db_session,
        sample_id=image.sample_id,
        embedding_model_id=other_model_id,
        embedding=[1.0, 0.0],
    )
    other_collection_id = create_collection(
        session=db_session, collection_name="other"
    ).collection_id
    other_image = create_image(
        session=db_session, collection_id=other_collection_id, file_path_abs="b.png"
    )
    create_sample_embedding(
        session=db_session,
        sample_id=other_image.sample_id,
        embedding_model_id=model_id,
        embedding=[0.0, 1.0],
    )

    similarity_range = similarity_range_resolver.get_similarity_range(
        session=db_session, collection_id=collection_id, text_embedding=[1.0, 0.0]
    )

    assert similarity_range is not None
    assert similarity_range.min == pytest.approx(0.7071, abs=1e-4)
    assert similarity_range.max == pytest.approx(0.7071, abs=1e-4)


def test_get_similarity_range__annotation_collection(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    image = create_image(session=db_session, collection_id=collection_id, file_path_abs="a.png")
    label = create_annotation_label(session=db_session, root_collection_id=collection_id)
    annotations = [
        create_annotation(
            session=db_session,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
            collection_id=collection_id,
        )
        for _ in range(2)
    ]
    annotation_collection_id = annotations[0].sample.collection_id
    model_id = create_embedding_model(
        session=db_session,
        collection_id=annotation_collection_id,
        embedding_dimension=2,
        set_as_default=True,
    ).embedding_model_id
    for annotation, embedding in zip(annotations, [[1.0, 0.0], [-1.0, 0.0]]):
        create_sample_embedding(
            session=db_session,
            sample_id=annotation.sample_id,
            embedding_model_id=model_id,
            embedding=embedding,
        )

    similarity_range = similarity_range_resolver.get_similarity_range(
        session=db_session, collection_id=annotation_collection_id, text_embedding=[1.0, 0.0]
    )

    assert similarity_range is not None
    assert similarity_range.min == pytest.approx(-1.0, abs=1e-6)
    assert similarity_range.max == pytest.approx(1.0, abs=1e-6)


def test_get_similarity_range__no_default_model(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    model_id = create_embedding_model(
        session=db_session, collection_id=collection_id, embedding_dimension=2
    ).embedding_model_id
    image = create_image(session=db_session, collection_id=collection_id, file_path_abs="a.png")
    create_sample_embedding(
        session=db_session,
        sample_id=image.sample_id,
        embedding_model_id=model_id,
        embedding=[1.0, 0.0],
    )

    similarity_range = similarity_range_resolver.get_similarity_range(
        session=db_session, collection_id=collection_id, text_embedding=[1.0, 0.0]
    )

    assert similarity_range is None


def test_get_similarity_range__no_embeddings(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    create_embedding_model(
        session=db_session, collection_id=collection_id, embedding_dimension=2, set_as_default=True
    )
    create_image(session=db_session, collection_id=collection_id, file_path_abs="a.png")

    similarity_range = similarity_range_resolver.get_similarity_range(
        session=db_session, collection_id=collection_id, text_embedding=[1.0, 0.0]
    )

    assert similarity_range is None
