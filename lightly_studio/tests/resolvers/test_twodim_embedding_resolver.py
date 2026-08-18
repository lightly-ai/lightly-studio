from __future__ import annotations

import numpy as np
from pytest_mock import MockerFixture
from sqlmodel import Session, select

from lightly_studio.models.two_dim_embedding import TwoDimEmbeddingTable
from lightly_studio.resolvers import twodim_embedding_resolver
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


def test_get_twodim_embeddings__no_samples(
    db_session: Session,
) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, collection_name="no_samples"
    )
    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_dimension=3,
    )

    x_values, y_values, sample_ids = twodim_embedding_resolver.get_twodim_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    assert len(x_values) == 0
    assert len(y_values) == 0
    assert sample_ids == []


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


def test_get_twodim_embeddings__identical_embeddings_do_not_share_cache(
    db_session: Session,
) -> None:
    """Two collections with identical embeddings get their own cache row.

    The cache is keyed by (collection, embedding model), so collections whose embeddings
    hash identically must not read each other's coordinates.
    """
    collections = []
    for name in ("collection_a", "collection_b"):
        collection = helpers_resolvers.create_collection(session=db_session, collection_name=name)
        embedding_model = helpers_resolvers.create_embedding_model(
            session=db_session,
            collection_id=collection.collection_id,
            embedding_dimension=3,
        )
        helpers_resolvers.create_samples_with_embeddings(
            session=db_session,
            collection_id=collection.collection_id,
            embedding_model_id=embedding_model.embedding_model_id,
            # Identical embeddings in both collections.
            images_and_embeddings=[
                (ImageStub(path=f"{name}_1.jpg"), [0.1, 0.2, 0.3]),
                (ImageStub(path=f"{name}_2.jpg"), [0.4, 0.5, 0.6]),
            ],
        )
        collections.append((collection, embedding_model))

    results = [
        twodim_embedding_resolver.get_twodim_embeddings(
            session=db_session,
            collection_id=collection.collection_id,
            embedding_model_id=embedding_model.embedding_model_id,
        )
        for collection, embedding_model in collections
    ]

    # Each collection got its own row, holding its own sample ids.
    cached_rows = db_session.exec(select(TwoDimEmbeddingTable)).all()
    assert len(cached_rows) == 2
    assert {row.collection_id for row in cached_rows} == {
        collection.collection_id for collection, _ in collections
    }
    sample_ids_a, sample_ids_b = results[0][2], results[1][2]
    assert set(sample_ids_a).isdisjoint(sample_ids_b)


def test_get_twodim_embeddings__recompute_overwrites_existing_row(
    db_session: Session,
) -> None:
    """Recomputing over an existing key updates the row instead of raising."""
    collection = helpers_resolvers.create_collection(
        session=db_session, collection_name="overwrite_collection"
    )
    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_dimension=3,
    )
    first_sample = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/overwrite_0.jpg",
    )
    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=first_sample.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.1, 0.1, 0.1],
    )
    twodim_embedding_resolver.get_twodim_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )
    fingerprint_before = db_session.exec(select(TwoDimEmbeddingTable)).one().fingerprint

    # Change the sample set so the next call recomputes over the same key.
    second_sample = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/overwrite_1.jpg",
    )
    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=second_sample.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.2, 0.2, 0.2],
    )
    twodim_embedding_resolver.get_twodim_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    cached_rows = db_session.exec(select(TwoDimEmbeddingTable)).all()
    assert len(cached_rows) == 1
    assert cached_rows[0].fingerprint != fingerprint_before
    assert len(cached_rows[0].sample_ids) == 2


def test_get_twodim_embeddings__cached_row_with_mismatched_lengths_recomputes(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """A cached row whose arrays disagree in length is recomputed instead of returned.

    Callers zip the coordinates with the sample ids, so returning a row where the two
    differ in length would fail downstream rather than here.
    """
    collection = helpers_resolvers.create_collection(
        session=db_session, collection_name="mismatch_collection"
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
            (ImageStub(path="mismatch_1.jpg"), [0.1, 0.2, 0.3]),
            (ImageStub(path="mismatch_2.jpg"), [0.4, 0.5, 0.6]),
        ],
    )
    _, _, sample_ids = twodim_embedding_resolver.get_twodim_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    # Corrupt the cached row: drop one coordinate pair but keep both sample ids.
    cached = db_session.exec(select(TwoDimEmbeddingTable)).one()
    cached.x = cached.x[:1]
    cached.y = cached.y[:1]
    db_session.add(cached)
    db_session.commit()

    calculate_spy = mocker.spy(twodim_embedding_resolver, "_calculate_2d_embeddings")
    x_values, y_values, sample_ids_after = twodim_embedding_resolver.get_twodim_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    calculate_spy.assert_called_once()
    assert len(x_values) == len(y_values) == len(sample_ids_after) == 2
    assert sorted(sample_ids_after, key=str) == sorted(sample_ids, key=str)
