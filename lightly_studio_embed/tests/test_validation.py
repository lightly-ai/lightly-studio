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
    """An embedder that read no input returns an empty array of any width."""
    result = EmbeddingResult(embeddings=np.empty((0, 0), dtype=np.float32), kept_indices=[])

    response = build_embeddings_response(
        result=result, space_key=SPACE_KEY, dimension=2, item_count=2
    )

    assert response.kept_indices == []
    assert response.embeddings == []


def test_build_embeddings_response__empty_array_that_still_has_a_row() -> None:
    """``np.empty((1, 0))`` is empty. It still holds one row, and no index names it."""
    result = EmbeddingResult(embeddings=np.empty((1, 0), dtype=np.float32), kept_indices=[])

    with pytest.raises(EmbedderContractError, match="1 embeddings for 0 kept indices"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=1)


def test_build_embeddings_response__kept_indices_out_of_range() -> None:
    """Only the server knows how many items the request carried."""
    result = EmbeddingResult(embeddings=np.array([[0.5, -0.5]], dtype=np.float32), kept_indices=[3])

    with pytest.raises(EmbedderContractError, match="must point into the 2 items"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=2)


def test_build_embeddings_response__negative_kept_index() -> None:
    """The wire model owns this rule. The error still names the embedder."""
    result = EmbeddingResult(
        embeddings=np.array([[0.5, -0.5]], dtype=np.float32), kept_indices=[-1]
    )

    with pytest.raises(EmbedderContractError, match="greater than or equal to 0"):
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
    """A flat array holds the right number of values. It holds no rows."""
    result = EmbeddingResult(embeddings=np.array([0.5, -0.5], dtype=np.float32), kept_indices=[0])

    with pytest.raises(EmbedderContractError, match="Got 1 dimensions"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=1)


def test_build_embeddings_response__value_not_finite() -> None:
    result = EmbeddingResult(
        embeddings=np.array([[0.5, np.nan]], dtype=np.float32), kept_indices=[0]
    )

    with pytest.raises(EmbedderContractError, match="not finite"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=1)


def test_build_embeddings_response__value_too_large_for_a_float32() -> None:
    """A float64 array holds 1e300. The float32 of the database makes it an infinity."""
    result = EmbeddingResult(
        embeddings=np.array([[1e300, 1.0]], dtype=np.float64),
        kept_indices=[0],
    )

    with pytest.raises(EmbedderContractError, match="would become an infinity"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=1)


def test_build_embeddings_response__kept_index_not_integral() -> None:
    """The model rejects a float index. It does not truncate the index onto the wrong item."""
    result = EmbeddingResult(
        embeddings=np.array([[0.5, -0.5]], dtype=np.float32),
        kept_indices=[0.9],  # type: ignore[list-item]
    )

    with pytest.raises(EmbedderContractError, match="valid integer"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=2)


def test_build_embeddings_response__kept_indices_are_a_boolean_mask() -> None:
    """A lax int field converts a bool into 0 or 1. A mask must not pass for indices."""
    result = EmbeddingResult(
        embeddings=np.array([[0.5, -0.5]], dtype=np.float32),
        kept_indices=[False, True],
    )

    with pytest.raises(EmbedderContractError, match="bool, not an index"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=2)


def test_build_embeddings_response__kept_indices_are_a_numpy_boolean_mask() -> None:
    """``np.bool_`` is not a ``bool``. A lax int field still converts it."""
    result = EmbeddingResult(
        embeddings=np.array([[0.5, -0.5]], dtype=np.float32),
        kept_indices=list(np.array([False, True])),
    )

    with pytest.raises(EmbedderContractError, match="bool, not an index"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=2)


def test_build_embeddings_response__kept_indices_hold_numpy_integers() -> None:
    """``np.int64`` is a valid index. An embedder produces one often."""
    result = EmbeddingResult(
        embeddings=np.array([[0.5, -0.5]], dtype=np.float32),
        kept_indices=list(np.array([1])),
    )

    response = build_embeddings_response(
        result=result, space_key=SPACE_KEY, dimension=2, item_count=2
    )

    assert response.kept_indices == [1]


def test_build_embeddings_response__ragged_rows() -> None:
    """Ragged rows do not make a numeric array. The result is not an array at all."""
    result = EmbeddingResult(
        embeddings=[[0.5, -0.5], [1.0]],  # type: ignore[arg-type]
        kept_indices=[0, 1],
    )

    with pytest.raises(EmbedderContractError, match="must be a numpy array"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=2)


def test_build_embeddings_response__values_not_numbers() -> None:
    result = EmbeddingResult(
        embeddings=np.array([["not a number", 1.0]]),
        kept_indices=[0],
    )

    with pytest.raises(EmbedderContractError, match="must hold numbers"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=1)


def test_build_embeddings_response__a_none_among_the_values() -> None:
    """``np.asarray`` maps ``None`` onto a NaN. The dtype names the fault."""
    result = EmbeddingResult(
        embeddings=np.array([[None, 1.0]]),
        kept_indices=[0],
    )

    with pytest.raises(EmbedderContractError, match="must hold numbers"):
        build_embeddings_response(result=result, space_key=SPACE_KEY, dimension=2, item_count=1)
