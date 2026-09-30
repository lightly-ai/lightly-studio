from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError
from sqlmodel import Session, col, select

from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.similarity_threshold_filter import SimilarityThresholdFilter
from lightly_studio.type_definitions import QueryType
from tests.helpers_resolvers import (
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
)


class _ThresholdFilter(SimilarityThresholdFilter):
    """Minimal filter exposing the mixin's threshold predicate on ``SampleTable``."""

    def apply(self, query: QueryType) -> QueryType:
        return self._apply_similarity_threshold_filter(
            query, sample_id_column=col(SampleTable.sample_id)
        )


def test_init__min_similarity_requires_text_embedding() -> None:
    with pytest.raises(ValidationError, match="min_similarity requires text_embedding"):
        _ThresholdFilter(min_similarity=0.5)


@pytest.mark.parametrize("min_similarity", [-1.5, 1.5])
def test_init__min_similarity_out_of_range(min_similarity: float) -> None:
    with pytest.raises(ValidationError):
        _ThresholdFilter(text_embedding=[1.0], min_similarity=min_similarity)


def test_apply__no_threshold_does_not_filter(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="a.png"
    )

    query = _ThresholdFilter(text_embedding=[1.0, 0.0]).apply(select(SampleTable.sample_id))

    assert set(db_session.exec(query).all()) == {image.sample_id}


def test_apply__keeps_samples_at_or_above_min_similarity(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    model_id = create_embedding_model(
        session=db_session, collection_id=collection_id, embedding_dimension=2, set_as_default=True
    ).embedding_model_id
    # Similarities to [1, 0]: 1.0, ~0.707 and 0.0.
    same = _create_image_with_embedding(
        session=db_session, collection_id=collection_id, model_id=model_id, embedding=[1.0, 0.0]
    )
    diagonal = _create_image_with_embedding(
        session=db_session, collection_id=collection_id, model_id=model_id, embedding=[1.0, 1.0]
    )
    _create_image_with_embedding(
        session=db_session, collection_id=collection_id, model_id=model_id, embedding=[0.0, 1.0]
    )

    threshold_filter = _ThresholdFilter(
        text_embedding=[1.0, 0.0],
        min_similarity=0.7,
    )
    query = threshold_filter.apply(select(SampleTable.sample_id))

    assert set(db_session.exec(query).all()) == {same.sample_id, diagonal.sample_id}


def test_apply__negative_min_similarity(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    model_id = create_embedding_model(
        session=db_session, collection_id=collection_id, embedding_dimension=2, set_as_default=True
    ).embedding_model_id
    # Similarities to [1, 0]: 1.0, ~-0.707 and -1.0.
    same = _create_image_with_embedding(
        session=db_session, collection_id=collection_id, model_id=model_id, embedding=[1.0, 0.0]
    )
    obtuse = _create_image_with_embedding(
        session=db_session, collection_id=collection_id, model_id=model_id, embedding=[-1.0, 1.0]
    )
    _create_image_with_embedding(
        session=db_session, collection_id=collection_id, model_id=model_id, embedding=[-1.0, 0.0]
    )

    threshold_filter = _ThresholdFilter(
        text_embedding=[1.0, 0.0],
        min_similarity=-0.8,
    )
    query = threshold_filter.apply(select(SampleTable.sample_id))

    assert set(db_session.exec(query).all()) == {same.sample_id, obtuse.sample_id}


def test_apply__ignores_embeddings_of_non_default_models(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    default_model_id = create_embedding_model(
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
    image = _create_image_with_embedding(
        session=db_session,
        collection_id=collection_id,
        model_id=default_model_id,
        embedding=[0.0, 1.0],
    )
    create_sample_embedding(
        session=db_session,
        sample_id=image.sample_id,
        embedding_model_id=other_model_id,
        embedding=[1.0, 0.0],
    )

    threshold_filter = _ThresholdFilter(text_embedding=[1.0, 0.0], min_similarity=0.5)
    query = threshold_filter.apply(select(SampleTable.sample_id))

    assert db_session.exec(query).all() == []


def test_apply__uses_default_model_of_each_sample_collection(db_session: Session) -> None:
    collection_a_id = create_collection(session=db_session, collection_name="a").collection_id
    collection_b_id = create_collection(session=db_session, collection_name="b").collection_id
    model_a_id = create_embedding_model(
        session=db_session,
        collection_id=collection_a_id,
        embedding_model_name="model_a",
        embedding_dimension=2,
        set_as_default=True,
    ).embedding_model_id
    model_b_id = create_embedding_model(
        session=db_session,
        collection_id=collection_b_id,
        embedding_model_name="model_b",
        embedding_dimension=2,
        set_as_default=True,
    ).embedding_model_id
    image_a = _create_image_with_embedding(
        session=db_session, collection_id=collection_a_id, model_id=model_a_id, embedding=[1.0, 0.0]
    )
    image_b = _create_image_with_embedding(
        session=db_session, collection_id=collection_b_id, model_id=model_b_id, embedding=[1.0, 0.0]
    )
    # An embedding of the default model of collection a does not count for collection b.
    create_sample_embedding(
        session=db_session,
        sample_id=image_b.sample_id,
        embedding_model_id=model_a_id,
        embedding=[0.0, 1.0],
    )

    threshold_filter = _ThresholdFilter(text_embedding=[1.0, 0.0], min_similarity=0.9)
    query = threshold_filter.apply(select(SampleTable.sample_id))

    assert set(db_session.exec(query).all()) == {image_a.sample_id, image_b.sample_id}


def test_apply__collection_without_default_model_matches_nothing(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    model_id = create_embedding_model(
        session=db_session, collection_id=collection_id, embedding_dimension=2
    ).embedding_model_id
    _create_image_with_embedding(
        session=db_session, collection_id=collection_id, model_id=model_id, embedding=[1.0, 0.0]
    )

    threshold_filter = _ThresholdFilter(text_embedding=[1.0, 0.0], min_similarity=0.5)
    query = threshold_filter.apply(select(SampleTable.sample_id))

    assert db_session.exec(query).all() == []


def _create_image_with_embedding(
    session: Session,
    collection_id: uuid.UUID,
    model_id: uuid.UUID,
    embedding: list[float],
) -> ImageTable:
    image = create_image(
        session=session,
        collection_id=collection_id,
        file_path_abs=f"{uuid.uuid4()}.png",
    )
    create_sample_embedding(
        session=session,
        sample_id=image.sample_id,
        embedding_model_id=model_id,
        embedding=embedding,
    )
    return image
