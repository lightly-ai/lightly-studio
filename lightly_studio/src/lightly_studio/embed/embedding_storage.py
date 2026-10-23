"""Validation and persistence for generated sample embeddings."""

from __future__ import annotations

from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlmodel import Session
from tqdm import tqdm

from lightly_studio.models.sample_embedding import SampleEmbeddingCreate
from lightly_studio.resolvers import embedding_model_resolver, sample_embedding_resolver
from lightly_studio.utils import batching

# Number of embeddings inserted per database round-trip. Larger batches mean fewer
# round-trips but higher peak memory. 1024 balances the two.
EMBEDDING_INSERTION_BATCH_SIZE = 1024


def store_embeddings(  # noqa: PLR0913
    session: Session,
    model_id: UUID,
    sample_ids: list[UUID],
    embeddings: NDArray[np.float32],
    show_progress: bool = True,
    replace: bool = False,
    source_fingerprints: list[str] | None = None,
) -> None:
    """Store embeddings in the database.

    Insertion is batched to reduce peak memory. All batches of one call are committed
    together. A caller that embeds in chunks calls this once per chunk, so a failure
    keeps the chunks stored before it.

    Args:
        session: Database session.
        model_id: ID of the embedding model that produced the embeddings.
        sample_ids: Sample IDs, one per row of `embeddings`.
        embeddings: Array of shape (N, D) with one row per sample.
        show_progress: Whether to show a progress bar.
        replace: If True, overwrite an existing embedding of the same sample and model.
            If False, keep the existing embedding.
        source_fingerprints: Optional fingerprints, one per sample ID. Row i is stored with
            `embeddings[i]`. If None, the stored fingerprints are None.

    Raises:
        ValueError: If there is not one fingerprint per sample ID, or the embeddings fail
            validation. See `_validate_and_coerce_embeddings`.
    """
    if source_fingerprints is not None and len(source_fingerprints) != len(sample_ids):
        raise ValueError(
            f"Number of fingerprints ({len(source_fingerprints)}) does not match number of "
            f"sample IDs ({len(sample_ids)})."
        )
    embeddings = _validate_and_coerce_embeddings(
        session=session, model_id=model_id, sample_ids=sample_ids, embeddings=embeddings
    )

    fingerprints: list[str | None] = (
        [None] * len(sample_ids) if source_fingerprints is None else list(source_fingerprints)
    )

    with tqdm(
        total=len(sample_ids),
        desc="Storing embeddings",
        unit=" embeddings",
        disable=not show_progress,
    ) as progress:
        for batch in batching.batched(
            items=zip(sample_ids, embeddings, fingerprints),
            batch_size=EMBEDDING_INSERTION_BATCH_SIZE,
        ):
            sample_embeddings = [
                SampleEmbeddingCreate(
                    sample_id=sample_id,
                    embedding_model_id=model_id,
                    embedding=embedding,
                    source_fingerprint=fingerprint,
                )
                for sample_id, embedding, fingerprint in batch
            ]
            if replace:
                sample_embedding_resolver.upsert_many(
                    session=session, sample_embeddings=sample_embeddings, commit=False
                )
            else:
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
