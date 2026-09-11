"""Validation and persistence for generated sample embeddings."""

from __future__ import annotations

from uuid import UUID

import numpy as np
from lightly_studio_serve.types import EmbeddingResult
from numpy.typing import NDArray
from sqlmodel import Session
from tqdm import tqdm

from lightly_studio.models.sample_embedding import SampleEmbeddingCreate
from lightly_studio.resolvers import embedding_model_resolver, sample_embedding_resolver
from lightly_studio.utils import batching

# Number of embeddings inserted per database round-trip. Larger batches mean fewer
# round-trips but higher peak memory. 1024 balances the two.
EMBEDDING_INSERTION_BATCH_SIZE = 1024


def store_embedding_result(
    session: Session, model_id: UUID, sample_ids: list[UUID], result: EmbeddingResult
) -> None:
    """Validate kept input indices and store their corresponding sample embeddings."""
    indices = result.kept_indices
    if any(index < 0 or index >= len(sample_ids) for index in indices):
        raise ValueError("Embedding kept indices are out of range.")
    if any(left >= right for left, right in zip(indices, indices[1:])):
        raise ValueError("Embedding kept indices must be strictly increasing.")
    store_embeddings(
        session=session,
        model_id=model_id,
        sample_ids=[sample_ids[index] for index in indices],
        embeddings=result.embeddings,
    )


def store_embeddings(
    session: Session,
    model_id: UUID,
    sample_ids: list[UUID],
    embeddings: NDArray[np.float32],
    show_progress: bool = True,
) -> None:
    """Store embeddings in the database.

    Insertion is batched to reduce peak memory. All batches are committed together
    so a failure leaves no partially embedded dataset behind.

    Raises:
        ValueError: If the embeddings fail validation. See `_validate_and_coerce_embeddings`.
    """
    embeddings = _validate_and_coerce_embeddings(
        session=session, model_id=model_id, sample_ids=sample_ids, embeddings=embeddings
    )

    with tqdm(
        total=len(sample_ids),
        desc="Storing embeddings",
        unit=" embeddings",
        disable=not show_progress,
    ) as progress:
        for batch in batching.batched(
            items=zip(sample_ids, embeddings), batch_size=EMBEDDING_INSERTION_BATCH_SIZE
        ):
            sample_embeddings = [
                SampleEmbeddingCreate(
                    sample_id=sample_id,
                    embedding_model_id=model_id,
                    embedding=embedding,
                )
                for sample_id, embedding in batch
            ]
            sample_embedding_resolver.create_many(
                session=session, sample_embeddings=sample_embeddings, commit=False
            )

            progress.update(len(sample_embeddings))

    session.commit()


def _validate_and_coerce_embeddings(
    session: Session,
    model_id: UUID,
    sample_ids: list[UUID],
    embeddings: NDArray[np.float32],
) -> NDArray[np.float32]:
    """Validate embeddings and coerce them to float32 before they are stored.

    Any numeric dtype (e.g. float64, int32) is safely cast to float32. Losing precision
    beyond float32 is expected and fine; overflowing to Inf is not.

    Raises:
        ValueError: If the number of embeddings does not match the number of sample
            IDs, the embeddings are not a 2-D numeric array free of NaN/Inf (before or
            after the float32 cast), or their dimension does not match the embedding
            model's declared `embedding_dimension`.
    """
    if embeddings.ndim != 2:  # noqa: PLR2004
        raise ValueError(
            "Embeddings must be a 2-D array (one row per sample: shape "
            f"(num_samples, embedding_dimension)), got a {embeddings.ndim}-D array."
        )
    if embeddings.shape[0] != len(sample_ids):
        raise ValueError(
            f"Number of embeddings ({embeddings.shape[0]}) does not match number of "
            f"sample IDs ({len(sample_ids)})."
        )
    if embeddings.shape[0] == 0:
        return embeddings

    if not (
        np.issubdtype(embeddings.dtype, np.floating) or np.issubdtype(embeddings.dtype, np.integer)
    ):
        raise ValueError(f"Embeddings must be numeric, got dtype {embeddings.dtype}.")

    embeddings = embeddings.astype(np.float32, copy=False)
    if not np.isfinite(embeddings).all():
        raise ValueError("Embeddings must not contain NaN or infinite values.")

    embedding_model = embedding_model_resolver.get_by_id(
        session=session, embedding_model_id=model_id
    )
    if embedding_model is None:
        raise ValueError(f"No embedding model found with ID {model_id}")

    actual_dimension = embeddings.shape[1]
    if actual_dimension != embedding_model.embedding_dimension:
        raise ValueError(
            f"Embedding dimension ({actual_dimension}) does not match the embedding "
            f"model's declared dimension ({embedding_model.embedding_dimension})."
        )
    return embeddings
