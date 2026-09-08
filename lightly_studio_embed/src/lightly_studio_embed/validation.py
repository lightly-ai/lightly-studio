"""Checks an embedder's result against the contract before it leaves the server.

A wrong dimension or a NaN is far cheaper to find here, in the customer's own
process, than as a similarity search that misbehaves inside LightlyStudio.
"""

from __future__ import annotations

import math

from lightly_studio_embed.embedder import EmbeddingResult
from lightly_studio_embed.protocol import EmbeddingsResponse


class EmbedderContractError(RuntimeError):
    """Raised when an embedder returns a result the protocol does not allow."""


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
    kept_indices = list(result.kept_indices)
    embeddings = [[float(value) for value in row] for row in result.embeddings]
    _validate_kept_indices(kept_indices=kept_indices, item_count=item_count)
    _validate_embeddings(embeddings=embeddings, kept_count=len(kept_indices), dimension=dimension)
    return EmbeddingsResponse(
        space_key=space_key,
        dimension=dimension,
        kept_indices=kept_indices,
        embeddings=embeddings,
    )


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


def _validate_embeddings(*, embeddings: list[list[float]], kept_count: int, dimension: int) -> None:
    if len(embeddings) != kept_count:
        raise EmbedderContractError(
            f"Got {len(embeddings)} embeddings for {kept_count} kept indices; "
            f"the two must have the same length."
        )
    for index, row in enumerate(embeddings):
        if len(row) != dimension:
            raise EmbedderContractError(
                f"Embedding {index} has {len(row)} values, but the embedder declares "
                f"dimension {dimension}."
            )
        if not all(math.isfinite(value) for value in row):
            raise EmbedderContractError(f"Embedding {index} holds a value that is not finite.")
