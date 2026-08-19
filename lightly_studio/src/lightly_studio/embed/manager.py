"""Embedder manager: owns the registry and stores embeddings for ingest."""

from __future__ import annotations

import logging
from typing import cast
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.embed.capability import EmbedderDescriptor
from lightly_studio.embed.protocols import Embedder
from lightly_studio.embed.random_embedder import RandomEmbedder
from lightly_studio.embed.registry import EmbedderRegistry
from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.models.sample_embedding import SampleEmbeddingCreate
from lightly_studio.resolvers import (
    embedding_model_resolver,
    image_resolver,
    sample_embedding_resolver,
)
from lightly_studio.utils import batching

logger = logging.getLogger(__name__)

# Number of embeddings inserted per database round-trip. Larger batches mean fewer
# round-trips but higher peak memory. 1024 balances the two.
EMBEDDING_INSERTION_BATCH_SIZE = 1024


class EmbedderManager:
    """Owns an embedder registry and stores embeddings for the ingest path.

    <span class="doc-badge doc-badge--beta">Beta</span>

    A ``RandomEmbedder`` is registered as the default so ingest always produces
    embeddings until a user registers their own embedder.
    """

    def __init__(self) -> None:
        """Initialize the manager with a default ``RandomEmbedder``."""
        self._registry = EmbedderRegistry()
        self._registry.register(RandomEmbedder())

    def register(self, embedder: Embedder) -> None:
        """Register an embedder, overriding the default for its capabilities.

        Args:
            embedder: The embedder to register.
        """
        self._registry.register(embedder)

    def embed_images_and_store(
        self, session: Session, collection_id: UUID, sample_ids: list[UUID]
    ) -> None:
        """Embed the images for ``sample_ids`` and store the vectors.

        Args:
            session: Database session for resolver operations.
            collection_id: Collection the embedding model belongs to.
            sample_ids: Sample IDs of the images to embed.
        """
        if not sample_ids:
            return
        embedder = self._registry.get_default_image_path_embedder()
        if embedder is None:
            logger.warning("No image-path embedder registered. Skipping embedding generation.")
            return

        # Every registered embedder also implements the Embedder protocol; the
        # capability slot only narrows to the image-path protocol.
        descriptor = cast(Embedder, embedder).describe()
        db_model = embedding_model_resolver.get_or_create(
            session=session,
            embedding_model=_to_embedding_model_create(
                descriptor=descriptor, collection_id=collection_id
            ),
        )

        paths = _get_filepaths_in_order(session=session, sample_ids=sample_ids)
        result = embedder.embed_images(paths)
        kept_sample_ids = [sample_ids[index] for index in result.kept_indices]
        _store_embeddings(
            session=session,
            model_id=db_model.embedding_model_id,
            sample_ids=kept_sample_ids,
            embeddings=result.embeddings,
        )


class EmbedderManagerProvider:
    """Provider for the ``EmbedderManager`` singleton instance.

    <span class="doc-badge doc-badge--beta">Beta</span>
    """

    _instance: EmbedderManager | None = None

    @classmethod
    def get_embedder_manager(cls) -> EmbedderManager:
        """Return the singleton ``EmbedderManager``, creating it on first use."""
        if cls._instance is None:
            cls._instance = EmbedderManager()
        return cls._instance


def register_default_embedder(embedder: Embedder) -> None:
    """Register an embedder as the default for the capabilities it offers.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Call this before you add a dataset to use your own embedder instead of the
    built-in ``RandomEmbedder``.

    Args:
        embedder: The embedder to register.
    """
    EmbedderManagerProvider.get_embedder_manager().register(embedder)


def _to_embedding_model_create(
    descriptor: EmbedderDescriptor, collection_id: UUID
) -> EmbeddingModelCreate:
    """Adapt an ``EmbedderDescriptor`` to the existing ``EmbeddingModelCreate``.

    The ``model_id`` is a stable identity string, so it is used for both the row
    name and the hash that matches the model across runs.
    """
    return EmbeddingModelCreate(
        name=descriptor.model_id,
        embedding_model_hash=descriptor.model_id,
        embedding_dimension=descriptor.dimension,
        collection_id=collection_id,
    )


def _get_filepaths_in_order(session: Session, sample_ids: list[UUID]) -> list[str]:
    """Return the absolute image paths for ``sample_ids``, in the same order."""
    sample_id_to_filepath = {
        sample.sample_id: sample.file_path_abs
        for sample in image_resolver.get_many_by_id(session=session, sample_ids=sample_ids)
    }
    return [sample_id_to_filepath[sample_id] for sample_id in sample_ids]


def _store_embeddings(
    session: Session,
    model_id: UUID,
    sample_ids: list[UUID],
    embeddings: NDArray[np.float32],
) -> None:
    """Store embeddings in the database.

    Insertion is batched to reduce peak memory. All batches are committed together
    so a failure leaves no partially embedded dataset behind.
    """
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
    session.commit()
