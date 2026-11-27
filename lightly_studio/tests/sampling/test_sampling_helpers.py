"""Tests for the shared sampling database helpers."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.sampling import sampling_helpers
from tests.sampling import helpers_sampling


def test_get_sample_ids_with_embeddings(db_session: Session) -> None:
    collection_id, sample_ids = helpers_sampling.create_images_with_embeddings(
        session=db_session,
        embeddings_per_image=[
            {"a": [0.0], "b": [0.0]},
            {"a": [1.0]},
            {"b": [2.0]},
            {"a": [3.0], "b": [3.0]},
        ],
    )

    embedded_sample_ids = sampling_helpers.get_sample_ids_with_embeddings(
        session=db_session,
        collection_id=collection_id,
        sample_ids=sample_ids,
        embedding_model_names=["a", "b"],
    )

    assert embedded_sample_ids == {sample_ids[0], sample_ids[3]}


def test_get_sample_ids_with_embeddings__no_models(db_session: Session) -> None:
    collection_id, sample_ids = helpers_sampling.create_images_with_embeddings(
        session=db_session,
        embeddings_per_image=[{"a": [0.0]}, {}],
    )

    embedded_sample_ids = sampling_helpers.get_sample_ids_with_embeddings(
        session=db_session,
        collection_id=collection_id,
        sample_ids=sample_ids,
        embedding_model_names=[],
    )

    assert embedded_sample_ids == set(sample_ids)
