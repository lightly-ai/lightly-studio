from __future__ import annotations

from unittest import mock

import numpy as np
import pytest
from pytest_mock import MockerFixture
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlmodel import Session, create_engine

from lightly_studio.models.embedding_plot import EmbeddingPlotTable
from lightly_studio.models.sample_embedding import SampleEmbeddingCreate
from lightly_studio.resolvers import sample_embedding_resolver, twodim_embedding_resolver
from tests import helpers_resolvers
from tests.helpers_resolvers import (
    ImageStub,
)


def test__calculate_2d_embeddings__1_sample() -> None:
    embedding_values = [np.array([0.1, 0.2, 0.3], dtype=np.float32)]
    projected = twodim_embedding_resolver._calculate_2d_embeddings(embedding_values)
    assert projected == [(0.0, 0.0)]


def test__calculate_2d_embeddings__2_samples() -> None:
    embedding_values = [
        np.array([0.1, 0.2, 0.3], dtype=np.float32),
        np.array([0.4, 0.5, 0.6], dtype=np.float32),
    ]
    projected = twodim_embedding_resolver._calculate_2d_embeddings(embedding_values)
    assert projected == [(0.0, 0.0), (1.0, 1.0)]


@pytest.mark.parametrize("existing", [False, True])
def test_get_twodim_embeddings__write_during_rebuild(db_session: Session, existing: bool) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, collection_name="no_samples"
    )
    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_dimension=3,
    )

    sample = helpers_resolvers.create_image(
        session=db_session, collection_id=collection.collection_id
    )
    key = (collection.collection_id, embedding_model.embedding_model_id)
    if existing:
        db_session.add(EmbeddingPlotTable(collection_id=key[0], embedding_model_id=key[1]))
        db_session.commit()
    engine = create_engine(db_session.connection().engine.url)
    with Session(engine) as writer:

        def calculate(_embedding_values: object) -> list[tuple[float, float]]:
            # Fail promptly instead of blocking this synchronous test on the rebuild lock.
            if engine.dialect.name == "postgresql":
                writer.execute(text("SET LOCAL lock_timeout = '100ms'"))
            with pytest.raises(DBAPIError, match=r"[Cc]onflict|lock timeout"):
                sample_embedding_resolver.create_many(session=writer, sample_embeddings=[embedding])
            writer.rollback()
            return []

        embedding = SampleEmbeddingCreate(
            sample_id=sample.sample_id,
            embedding_model_id=key[1],
            embedding=np.ones(embedding_model.embedding_dimension, dtype=np.float32),
        )
        with mock.patch.object(
            twodim_embedding_resolver, "_calculate_2d_embeddings", side_effect=calculate
        ):
            _, _, ids = twodim_embedding_resolver.get_twodim_embeddings(
                session=db_session, collection_id=key[0], embedding_model_id=key[1]
            )
            assert ids == []
        sample_embedding_resolver.create_many(session=writer, sample_embeddings=[embedding])
        assert twodim_embedding_resolver.get_twodim_embeddings(
            session=db_session, collection_id=key[0], embedding_model_id=key[1]
        )[2] == [sample.sample_id]
    engine.dispose()


def test_get_twodim_embeddings__no_samples_with_embeddings(
    db_session: Session,
) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, collection_name="missing_embeddings"
    )
    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_dimension=3,
    )
    helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="sample_missing_embedding.jpg",
    )

    x_values, y_values, sample_ids = twodim_embedding_resolver.get_twodim_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    assert len(x_values) == 0
    assert len(y_values) == 0
    assert sample_ids == []


def test_get_twodim_embeddings__cache_hit(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    # Create collection, embedding model, samples, and embeddings.
    collection = helpers_resolvers.create_collection(
        session=db_session, collection_name="cache_hit_collection"
    )
    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_dimension=3,
    )

    helpers_resolvers.create_samples_with_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        images_and_embeddings=[
            (ImageStub(path="sample_1.jpg"), [0.1, 0.2, 0.3]),
            (ImageStub(path="sample_2.jpg"), [0.4, 0.5, 0.6]),
        ],
    )
    calculate_spy = mocker.spy(twodim_embedding_resolver, "_calculate_2d_embeddings")

    # First call - should call _calculate_2d_embeddings.
    x_first, y_first, sample_ids_first_call = twodim_embedding_resolver.get_twodim_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )
    calculate_spy.assert_called_once()

    assert x_first.shape == (2,)
    assert y_first.shape == (2,)
    assert len(sample_ids_first_call) == 2

    for name in ("get_hash_by_collection_id", "get_all_by_collection_id", "get_by_sample_ids"):
        mocker.patch.object(sample_embedding_resolver, name, side_effect=AssertionError(name))
    # Second call - should use cache, not call _calculate_2d_embeddings again.
    x_second, y_second, sample_ids_second_call = twodim_embedding_resolver.get_twodim_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    calculate_spy.assert_called_once()
    np.testing.assert_allclose(x_first, x_second)
    np.testing.assert_allclose(y_first, y_second)
    assert sample_ids_first_call == sample_ids_second_call

    # Third call after adding a sample without embeddings - should still use cache.
    helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="sample_3.jpg",
    )
    x_third, y_third, sample_ids_third_call = twodim_embedding_resolver.get_twodim_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )
    calculate_spy.assert_called_once()
    np.testing.assert_allclose(x_first, x_third)
    np.testing.assert_allclose(y_first, y_third)
    assert sample_ids_first_call == sample_ids_third_call


def test_get_twodim_embeddings__recomputes_when_samples_change(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    # Create collection, embedding model, samples, and embeddings.
    collection = helpers_resolvers.create_collection(
        session=db_session, collection_name="cache_miss_collection"
    )
    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_dimension=3,
    )

    first_sample = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/sample_0.jpg",
    )
    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=first_sample.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.1, 0.1, 0.1],
    )

    calculate_spy = mocker.spy(twodim_embedding_resolver, "_calculate_2d_embeddings")

    # First call - should call _calculate_2d_embeddings.
    x_first, y_first, sample_ids_first = twodim_embedding_resolver.get_twodim_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    assert calculate_spy.call_count == 1
    assert x_first.shape == (1,)
    assert y_first.shape == (1,)
    assert len(sample_ids_first) == 1

    # Add another sample and embedding.
    second_sample = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/sample_1.jpg",
    )
    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=second_sample.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.2, 0.2, 0.2],
    )

    # Second call - should recompute since samples changed.
    x_second, y_second, sample_ids_second = twodim_embedding_resolver.get_twodim_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    assert calculate_spy.call_count == 2
    assert x_second.shape == (2,)
    assert y_second.shape == (2,)
    assert len(sample_ids_second) == 2


def test_get_twodim_embeddings_from_axes(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_dimension=3,
    )
    image_a, image_b = helpers_resolvers.create_samples_with_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        images_and_embeddings=[
            (ImageStub(path="a.jpg"), [1.0, 2.0, 3.0]),
            (ImageStub(path="b.jpg"), [4.0, 5.0, 6.0]),
        ],
    )

    x_values, y_values, sample_ids = twodim_embedding_resolver.get_twodim_embeddings_from_axes(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        direction_x=[1.0, 0.0, 0.0],
        direction_y=[0.0, 1.0, 0.0],
    )

    # The directions select the first and the second embedding value.
    assert dict(zip(sample_ids, zip(x_values.tolist(), y_values.tolist()))) == {
        image_a.sample_id: (1.0, 2.0),
        image_b.sample_id: (4.0, 5.0),
    }
