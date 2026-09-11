"""Checks the result of an embedder before the server sends it.

A broken result is cheap to find here, in the process of the customer. It is expensive to
find later, as a similarity search that gives bad results in LightlyStudio.

``EmbeddingsResponse`` holds every rule that a response body shows. This module does not
repeat them. It checks the two rules that the body cannot show: the embedder returned a
matrix of numbers, and each kept index names an item of this request.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from pydantic import ValidationError

from lightly_studio_serve.errors import EmbedderContractError
from lightly_studio_serve.protocol import EmbeddingsResponse
from lightly_studio_serve.types import EmbeddingResult

# Float, signed integer and unsigned integer. A `bool` array is a mask, and an `object`
# array holds anything.
_NUMERIC_DTYPE_KINDS = frozenset("fiu")


def build_embeddings_response(
    result: EmbeddingResult, space_key: str, dimension: int, item_count: int
) -> EmbeddingsResponse:
    """Check the result of an embedder and convert it into a wire response.

    Args:
        result: What the embedder returned.
        space_key: The embedding space of the embedder. The response repeats it.
        dimension: The vector length that the embedder declares.
        item_count: The number of items in the request.

    Returns:
        The response body for an embed endpoint.

    Raises:
        EmbedderContractError: If the result does not agree with the declared dimension,
            with the number of kept indices, or with the items of the request.
    """
    _validate_embeddings(result.embeddings)
    response = _to_response(result=result, space_key=space_key, dimension=dimension)
    _validate_kept_indices(kept_indices=response.kept_indices, item_count=item_count)
    return response


def _validate_embeddings(embeddings: NDArray[np.float32]) -> None:
    """Check that the embedder returned a matrix of numbers.

    The wire model reads lists, so it cannot tell an array from anything else that holds
    rows. Ragged rows and values that are not numbers never become a numeric array. Both
    fail here, with the reason named.
    """
    if not isinstance(embeddings, np.ndarray):
        raise EmbedderContractError(
            f"embeddings must be a numpy array, with every row the same length. "
            f"Got {type(embeddings).__name__}."
        )
    if embeddings.dtype.kind not in _NUMERIC_DTYPE_KINDS:
        raise EmbedderContractError(
            f"embeddings must hold numbers. Got an array of dtype {embeddings.dtype}."
        )
    # An embedder that kept no input returns an empty array of any shape. No row lines up
    # with an index. The wire model still rejects a kept index that has no row.
    if embeddings.ndim > 0 and embeddings.shape[0] == 0:
        return
    # A matrix has two axes: one of rows, one of the values in a row.
    if embeddings.ndim != 2:  # noqa: PLR2004
        raise EmbedderContractError(
            f"embeddings must hold one row for each kept index, so a 2D array. "
            f"Got {embeddings.ndim} dimensions."
        )


def _to_response(result: EmbeddingResult, space_key: str, dimension: int) -> EmbeddingsResponse:
    """Build the wire body, and name the embedder that broke one of its rules.

    The model raises for a client that reads a bad response. Here the embedder in this
    process is at fault, so the same rule becomes an ``EmbedderContractError``. The server
    then answers 500.
    """
    try:
        return EmbeddingsResponse(
            space_key=space_key,
            dimension=dimension,
            kept_indices=result.kept_indices,
            embeddings=result.embeddings.tolist(),
        )
    except ValidationError as error:
        raise EmbedderContractError(
            f"The embedder returned a result that the protocol does not allow: {error}"
        ) from error


def _validate_kept_indices(kept_indices: list[int], item_count: int) -> None:
    """Check that every kept index names an item of this request.

    The wire model rejects a negative index and a repeated one. Only the server knows how
    many items the request carried, so this function checks the upper bound.
    """
    if any(index >= item_count for index in kept_indices):
        raise EmbedderContractError(
            f"kept_indices must point into the {item_count} items of the request, "
            f"got {kept_indices}."
        )
