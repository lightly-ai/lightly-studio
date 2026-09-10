"""Caption embedding generation for the callers that create or change captions.

Wraps :class:`~lightly_studio.dataset.embedding_manager.EmbeddingManager` with the
default-model lookup, so a caption gets embedded the same way whether it is created
through the Python API, a dataset loader, or the HTTP API. Embedding is skipped, with a
warning, when no embedding model can be loaded.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.dataset.embedding_manager import EmbeddingManagerProvider
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver, sample_resolver

logger = logging.getLogger(__name__)


def embed_captions(session: Session, caption_sample_ids: Sequence[UUID]) -> None:
    """Generate and store embeddings for the given captions.

    Captions that already have an embedding or whose text is empty are skipped.

    Args:
        session: Database session for resolver operations.
        caption_sample_ids: Sample IDs of the captions to embed. They must all belong to
            the same caption collection, which holds for captions created together.
    """
    if not caption_sample_ids:
        return

    caption_sample = sample_resolver.get_by_id(session=session, sample_id=caption_sample_ids[0])
    if caption_sample is None:
        return

    _embed_captions(
        session=session,
        caption_collection_id=caption_sample.collection_id,
        caption_sample_ids=caption_sample_ids,
    )


def embed_collection_captions(session: Session, root_collection_id: UUID) -> None:
    """Generate and store embeddings for all captions of a collection that lack one.

    Args:
        session: Database session for resolver operations.
        root_collection_id: The collection whose caption child collection should receive
            embeddings. Does nothing if the collection has no captions.
    """
    caption_collection_id = collection_resolver.get_by_name(
        session=session,
        name=SampleType.CAPTION.value.lower(),
        parent_collection_id=root_collection_id,
    )
    if caption_collection_id is None:
        return

    _embed_captions(
        session=session, caption_collection_id=caption_collection_id, caption_sample_ids=None
    )


def _embed_captions(
    session: Session,
    caption_collection_id: UUID,
    caption_sample_ids: Sequence[UUID] | None,
) -> None:
    """Embed captions of a caption collection with the collection's default model."""
    embedding_manager = EmbeddingManagerProvider.get_embedding_manager()
    model_id = embedding_manager.load_or_get_default_model(
        session=session, collection_id=caption_collection_id
    )
    if model_id is None:
        logger.warning("No embedding model loaded. Skipping caption embedding generation.")
        return

    embedding_manager.embed_captions(
        session=session,
        caption_collection_id=caption_collection_id,
        sample_ids=caption_sample_ids,
        embedding_model_id=model_id,
    )
