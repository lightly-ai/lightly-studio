"""Checks an embedder's result against the contract before it leaves the server.

A wrong dimension or a NaN is far cheaper to find here, in the customer's own
process, than as a similarity search that misbehaves inside LightlyStudio.
"""

from __future__ import annotations

import operator

import numpy as np
from numpy.typing import NDArray

from lightly_studio_embed.errors import EmbedderContractError
from lightly_studio_embed.protocol import EmbeddingsResponse
from lightly_studio_embed.types import EmbeddingResult

# Embeddings are one row per kept input, so anything but a matrix is a broken result.
_EMBEDDINGS_NDIM = 2


def build_embeddings_response(
    *, result: EmbeddingResult, space_key: str, dimension: int, item_count: int
) -> EmbeddingsResponse:
    """Validate an embedder's result and convert it into a wire response.

    Args:
        result: What the embedder returned.
        space_key: The embedder's embedding space, echoed on the response.
        dimension: The vector length the embedder declares.
        item_count: How many items the request carried.

    Returns:
        The response body for any embed endpoint.

    Raises:
        EmbedderContractError: If the result does not match the declared dimension,
            the number of kept indices, or the items of the request.
    """
    kept_indices = _as_indices(kept_indices=result.kept_indices)
    embeddings = _as_array(embeddings=result.embeddings)
    _validate_kept_indices(kept_indices=kept_indices, item_count=item_count)
    _validate_embeddings(embeddings=embeddings, kept_count=len(kept_indices), dimension=dimension)
    return EmbeddingsResponse(
        space_key=space_key,
        dimension=dimension,
        kept_indices=kept_indices,
        embeddings=embeddings.tolist(),
    )


def _as_indices(*, kept_indices: list[int]) -> list[int]:
    """Read the kept indices as plain integers, so a non-integral one fails here.

    ``operator.index`` rather than ``int``, which would truncate a float index and line the
    embeddings up against the wrong request items.
    """
    try:
        return [_as_index(index) for index in kept_indices]
    except (OverflowError, TypeError, ValueError) as error:
        raise EmbedderContractError(f"kept_indices must hold integers: {error}") from error


def _as_index(index: int) -> int:
    """Read one kept index, rejecting a bool so a mask cannot pass for a list of indices.

    ``np.bool_`` is checked separately, as it is not a subclass of ``bool`` but
    ``operator.index`` accepts it.
    """
    if isinstance(index, (bool, np.bool_)):
        raise TypeError(f"{index!r} is a bool, not an index")
    return operator.index(index)


def _as_array(*, embeddings: NDArray[np.float32]) -> NDArray[np.float64]:
    """Read the embeddings as a float matrix, so a non-numeric or ragged row fails here.

    ``float64`` rather than the declared ``float32``, so a value too large for the
    narrower type is rejected instead of quietly becoming an infinity.
    """
    try:
        return np.asarray(embeddings, dtype=np.float64)
    except (OverflowError, TypeError, ValueError) as error:
        raise EmbedderContractError(
            f"every embedding must hold numbers, and all rows the same count: {error}"
        ) from error


def _validate_kept_indices(*, kept_indices: list[int], item_count: int) -> None:
    if any(index < 0 or index >= item_count for index in kept_indices):
        raise EmbedderContractError(
            f"kept_indices must point into the {item_count} items of the request, "
            f"got {kept_indices}."
        )
    if any(current >= following for current, following in zip(kept_indices, kept_indices[1:])):
        raise EmbedderContractError(
            f"kept_indices must be ascending and unique, got {kept_indices}."
        )


def _validate_embeddings(
    *, embeddings: NDArray[np.float64], kept_count: int, dimension: int
) -> None:
    # An embedder that kept nothing may say so with any empty array, so its width is moot.
    if kept_count == 0 and embeddings.size == 0:
        return
    if embeddings.ndim != _EMBEDDINGS_NDIM:
        raise EmbedderContractError(
            f"embeddings must have one row per kept index, so a 2D array, "
            f"got {embeddings.ndim} dimensions."
        )
    rows, values_per_row = embeddings.shape
    if rows != kept_count:
        raise EmbedderContractError(
            f"Got {rows} embeddings for {kept_count} kept indices; "
            f"the two must have the same length."
        )
    if values_per_row != dimension:
        raise EmbedderContractError(
            f"Every embedding has {values_per_row} values, but the embedder declares "
            f"dimension {dimension}."
        )
    if not np.isfinite(embeddings).all():
        raise EmbedderContractError("The embeddings hold a value that is not finite.")
