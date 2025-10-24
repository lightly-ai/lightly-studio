from __future__ import annotations

import numpy as np
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.resolvers import twodim_embedding_resolver
from tests.helpers_resolvers import (
    create_dataset,
    create_embedding_model,
    create_sample,
    create_sample_embedding,
)


def test__calculate_2d_embeddings__1_sample() -> None:
    embedding_values = [[0.1, 0.2, 0.3]]
    projected = twodim_embedding_resolver._calculate_2d_embeddings(embedding_values)
    assert projected == [(0.0, 0.0)]


def test__calculate_2d_embeddings__2_samples() -> None:
    embedding_values = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    projected = twodim_embedding_resolver._calculate_2d_embeddings(embedding_values)
    assert projected == [(0.0, 0.0), (1.0, 1.0)]


def test__get_twodim_embeddings__cache_hit(
    test_db: Session,
    mocker: MockerFixture,
) -> None:
    # Create dataset, embedding model, samples, and embeddings.
    dataset = create_dataset(session=test_db, dataset_name="cache_hit_dataset")
    embedding_model = create_embedding_model(
        session=test_db,
        dataset_id=dataset.dataset_id,
        embedding_model_name="cache_hit_model",
        embedding_model_hash="cache_hit_hash",
        embedding_dimension=3,
    )

    embeddings = [
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6],
    ]
    for index, embedding in enumerate(embeddings):
        sample = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs=f"/sample_{index}.jpg",
        )
        create_sample_embedding(
            session=test_db,
            sample_id=sample.sample_id,
            embedding_model_id=embedding_model.embedding_model_id,
            embedding=embedding,
        )

    calculate_spy = mocker.spy(twodim_embedding_resolver, "_calculate_2d_embeddings")

    # First call - should call _calculate_2d_embeddings.
    x_first, y_first, sample_ids_first_call = twodim_embedding_resolver.get_twodim_embeddings(
        session=test_db,
        dataset_id=dataset.dataset_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )
    calculate_spy.assert_called_once()

    assert x_first.shape == (2,)
    assert y_first.shape == (2,)
    assert len(sample_ids_first_call) == 2

    # Second call - should use cache, not call _calculate_2d_embeddings again.
    x_second, y_second, sample_ids_second_call = twodim_embedding_resolver.get_twodim_embeddings(
        session=test_db,
        dataset_id=dataset.dataset_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    calculate_spy.assert_called_once()
    np.testing.assert_allclose(x_first, x_second)
    np.testing.assert_allclose(y_first, y_second)
    assert sample_ids_first_call == sample_ids_second_call


def test__get_twodim_embeddings__recomputes_when_samples_change(
    test_db: Session,
    mocker: MockerFixture,
) -> None:
    # Create dataset, embedding model, samples, and embeddings.
    dataset = create_dataset(session=test_db, dataset_name="cache_miss_dataset")
    embedding_model = create_embedding_model(
        session=test_db,
        dataset_id=dataset.dataset_id,
        embedding_model_name="cache_miss_model",
        embedding_model_hash="cache_miss_hash",
        embedding_dimension=3,
    )

    first_sample = create_sample(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/sample_0.jpg",
    )
    create_sample_embedding(
        session=test_db,
        sample_id=first_sample.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.1, 0.1, 0.1],
    )

    calculate_spy = mocker.spy(twodim_embedding_resolver, "_calculate_2d_embeddings")

    # First call - should call _calculate_2d_embeddings.
    x_first, y_first, sample_ids_first = twodim_embedding_resolver.get_twodim_embeddings(
        session=test_db,
        dataset_id=dataset.dataset_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    assert calculate_spy.call_count == 1
    assert x_first.shape == (1,)
    assert y_first.shape == (1,)
    assert len(sample_ids_first) == 1

    # Add another sample and embedding.
    second_sample = create_sample(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/sample_1.jpg",
    )
    create_sample_embedding(
        session=test_db,
        sample_id=second_sample.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.2, 0.2, 0.2],
    )

    # Second call - should recompute since samples changed.
    x_second, y_second, sample_ids_second = twodim_embedding_resolver.get_twodim_embeddings(
        session=test_db,
        dataset_id=dataset.dataset_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    assert calculate_spy.call_count == 2
    assert x_second.shape == (2,)
    assert y_second.shape == (2,)
    assert len(sample_ids_second) == 2
