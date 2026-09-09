from __future__ import annotations

import numpy as np
import pytest

from lightly_studio_embed.errors import EmbedderContractError
from lightly_studio_embed.types import EmbeddingResult
from lightly_studio_embed.validation import build_embeddings_response

SPACE_KEY = "acme/model@v1"


def test_build_embeddings_response() -> None:
    result = EmbeddingResult(
        embeddings=np.array([[0.5, -0.5], [1.0, 0.0]], dtype=np.float32), kept_indices=[0, 2]
    )

    response = build_embeddings_response(
        result=result, space_key=SPACE_KEY, dimension=2, item_count=3
    )

    assert response.space_key == SPACE_KEY
    assert response.dimension == 2
    assert response.kept_indices == [0, 2]
    assert response.embeddings == [[0.5, -0.5], [1.0, 0.0]]


def test_build_embeddings_response__kept_nothing() -> None:
    """An embedder that could read no input says so with an empty array of any width."""
    result = EmbeddingResult(embeddings=np.empty((0, 2), dtype=np.float32), kept_indices=[])

    response = build_embeddings_response(
        result=result, space_key=SPACE_KEY, dimension=2, item_count=2
    )

    assert response.kept_indices == []
    assert response.embeddings == []


def test_build_embeddings_response__kept_indices_out_of_range() -> None:
    result = EmbeddingResult(embeddings=np.array([[0.5, -0.5]], dtype=np.float32), kept_indices=[3])

    with pytest.raises(EmbedderContractError, match="must point into the 2 items"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=2)


def test_build_embeddings_response__kept_indices_not_ascending() -> None:
    result = EmbeddingResult(
        embeddings=np.array([[0.5, -0.5], [1.0, 0.0]], dtype=np.float32), kept_indices=[1, 1]
    )

    with pytest.raises(EmbedderContractError, match="ascending and unique"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=2)


def test_build_embeddings_response__row_count_mismatch() -> None:
    result = EmbeddingResult(
        embeddings=np.array([[0.5, -0.5]], dtype=np.float32), kept_indices=[0, 1]
    )

    with pytest.raises(EmbedderContractError, match="1 embeddings for 2 kept indices"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=2)


def test_build_embeddings_response__wrong_dimension() -> None:
    result = EmbeddingResult(
        embeddings=np.array([[0.5, -0.5, 0.5]], dtype=np.float32), kept_indices=[0]
    )

    with pytest.raises(EmbedderContractError, match="has 3 values"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=1)


def test_build_embeddings_response__not_a_matrix() -> None:
    """A flat array of the right size still lines no row up with a kept index."""
    result = EmbeddingResult(embeddings=np.array([0.5, -0.5], dtype=np.float32), kept_indices=[0])

    with pytest.raises(EmbedderContractError, match="got 1 dimensions"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=1)


def test_build_embeddings_response__value_not_finite() -> None:
    result = EmbeddingResult(
        embeddings=np.array([[0.5, np.nan]], dtype=np.float32), kept_indices=[0]
    )

    with pytest.raises(EmbedderContractError, match="not finite"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=1)


def test_build_embeddings_response__kept_index_not_integral() -> None:
    """A float index is rejected rather than truncated onto the wrong request item."""
    result = EmbeddingResult(
        embeddings=np.array([[0.5, -0.5]], dtype=np.float32),
        kept_indices=[0.9],  # type: ignore[list-item]
    )

    with pytest.raises(EmbedderContractError, match="must hold integers"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=2)


def test_build_embeddings_response__kept_indices_are_a_boolean_mask() -> None:
    """A mask must not pass for indices, which is what bools would convert into."""
    result = EmbeddingResult(
        embeddings=np.array([[0.5, -0.5]], dtype=np.float32),
        kept_indices=[False, True],
    )

    with pytest.raises(EmbedderContractError, match="is a bool, not an index"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=2)


def test_build_embeddings_response__kept_indices_are_a_numpy_boolean_mask() -> None:
    """``np.bool_`` is not a ``bool``, but ``operator.index`` would still take it."""
    result = EmbeddingResult(
        embeddings=np.array([[0.5, -0.5]], dtype=np.float32),
        kept_indices=list(np.array([False, True])),
    )

    with pytest.raises(EmbedderContractError, match="is a bool, not an index"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=2)


def test_build_embeddings_response__ragged_rows() -> None:
    result = EmbeddingResult(
        embeddings=[[0.5, -0.5], [1.0]],  # type: ignore[arg-type]
        kept_indices=[0, 1],
    )

    with pytest.raises(EmbedderContractError, match="all rows the same count"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=2)


def test_build_embeddings_response__value_too_large_for_a_float() -> None:
    result = EmbeddingResult(
        embeddings=[[10**400, 1.0]],  # type: ignore[arg-type]
        kept_indices=[0],
    )

    with pytest.raises(EmbedderContractError, match="must hold numbers"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=1)


def test_build_embeddings_response__value_not_a_number() -> None:
    result = EmbeddingResult(
        embeddings=[["not a number", 1.0]],  # type: ignore[arg-type]
        kept_indices=[0],
    )

    with pytest.raises(EmbedderContractError, match="must hold numbers"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=1)
