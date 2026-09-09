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

EMBEDDING_INSERTION_BATCH_SIZE = 1024


def store_embeddings(
    session: Session,
    model_id: UUID,
    sample_ids: list[UUID],
    embeddings: NDArray[np.float32],
    show_progress: bool = True,
) -> None:
    """Validate and atomically store embeddings for sample IDs."""
    embeddings = validate_and_coerce_embeddings(
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
            rows = [
                SampleEmbeddingCreate(
                    sample_id=sample_id, embedding_model_id=model_id, embedding=embedding
                )
                for sample_id, embedding in batch
            ]
            sample_embedding_resolver.create_many(
                session=session, sample_embeddings=rows, commit=False
            )
            progress.update(len(rows))
    session.commit()


def validate_and_coerce_embeddings(
    session: Session,
    model_id: UUID,
    sample_ids: list[UUID],
    embeddings: NDArray[np.float32],
) -> NDArray[np.float32]:
    """Validate embedding shape, values, and persisted model dimension."""
    if embeddings.ndim != 2:  # noqa: PLR2004
        raise ValueError(f"Embeddings must be a 2-D array, got a {embeddings.ndim}-D array.")
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
    model = embedding_model_resolver.get_by_id(session=session, embedding_model_id=model_id)
    if model is None:
        raise ValueError(f"No embedding model found with ID {model_id}")
    if embeddings.shape[1] != model.embedding_dimension:
        raise ValueError(
            f"Embedding dimension ({embeddings.shape[1]}) does not match the embedding "
            f"model's declared dimension ({model.embedding_dimension})."
        )
    return embeddings
