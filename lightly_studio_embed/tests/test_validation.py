from __future__ import annotations

import pytest

from lightly_studio_embed.embedder import EmbeddingResult
from lightly_studio_embed.errors import EmbedderContractError
from lightly_studio_embed.validation import build_embeddings_response


def test_build_embeddings_response() -> None:
    result = EmbeddingResult(embeddings=[[0.5, -0.5], [1.0, 0.0]], kept_indices=[0, 2])

    response = build_embeddings_response(
        result=result, space_key="acme/model@v1", dimension=2, item_count=3
    )

    assert response.space_key == "acme/model@v1"
    assert response.dimension == 2
    assert response.kept_indices == [0, 2]
    assert response.embeddings == [[0.5, -0.5], [1.0, 0.0]]


def test_build_embeddings_response__kept_indices_out_of_range() -> None:
    result = EmbeddingResult(embeddings=[[0.5, -0.5]], kept_indices=[3])

    with pytest.raises(EmbedderContractError, match="must point into the 2 items"):
        build_embeddings_response(
            result=result, space_key="acme/model@v1", dimension=2, item_count=2
        )


def test_build_embeddings_response__kept_indices_not_ascending() -> None:
    result = EmbeddingResult(embeddings=[[0.5, -0.5], [1.0, 0.0]], kept_indices=[1, 1])

    with pytest.raises(EmbedderContractError, match="ascending and unique"):
        build_embeddings_response(
            result=result, space_key="acme/model@v1", dimension=2, item_count=2
        )


def test_build_embeddings_response__row_count_mismatch() -> None:
    result = EmbeddingResult(embeddings=[[0.5, -0.5]], kept_indices=[0, 1])

    with pytest.raises(EmbedderContractError, match="1 embeddings for 2 kept indices"):
        build_embeddings_response(
            result=result, space_key="acme/model@v1", dimension=2, item_count=2
        )


def test_build_embeddings_response__wrong_dimension() -> None:
    result = EmbeddingResult(embeddings=[[0.5, -0.5, 0.5]], kept_indices=[0])

    with pytest.raises(EmbedderContractError, match="has 3 values"):
        build_embeddings_response(
            result=result, space_key="acme/model@v1", dimension=2, item_count=1
        )


def test_build_embeddings_response__value_not_finite() -> None:
    result = EmbeddingResult(embeddings=[[0.5, float("nan")]], kept_indices=[0])

    with pytest.raises(EmbedderContractError, match="not finite"):
        build_embeddings_response(
            result=result, space_key="acme/model@v1", dimension=2, item_count=1
        )


def test_build_embeddings_response__value_not_a_number() -> None:
    result = EmbeddingResult(embeddings=[["not a number", 1.0]], kept_indices=[0])  # type: ignore[list-item]

    with pytest.raises(EmbedderContractError, match="must hold numbers"):
        build_embeddings_response(
            result=result, space_key="acme/model@v1", dimension=2, item_count=1
        )
