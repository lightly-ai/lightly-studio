"""Resolve the embedder and model id an embed function should use for a collection."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from lightly_studio_serve.embedder import Embedder
from sqlmodel import Session

from lightly_studio.embed import embedder_registry
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.resolvers import (
    collection_embedding_model_resolver,
    collection_resolver,
    embedding_model_resolver,
)

logger = logging.getLogger(__name__)

_EmbedderT = TypeVar("_EmbedderT", bound=Embedder)


def resolve_default_embedder(
    session: Session,
    collection_id: UUID,
    select_embedder: Callable[[EmbedderRegistry, str | None], _EmbedderT | None],
) -> tuple[_EmbedderT, UUID] | None:
    """Resolve the embedder and model id an embed function should use, or None to skip.

    Follows the pattern every ``embed_*`` function shares. ``select_embedder`` picks the
    capability the caller needs (image, text, ...) from the registry:

    - The collection has a default model: its embedding space selects the embedder.
    - The collection has no default yet: the registry's bootstrap embedder is used and
      registered as the collection's default.

    Logs a warning and returns None when the registry has no matching embedder, so the
    caller only needs to return on None.

    Args:
        session: Database session for resolver operations.
        collection_id: The collection whose default embedding model is used.
        select_embedder: Given the registry and a space key (None for the registry default),
            returns the embedder for the needed capability, or None if none matches.

    Returns:
        The embedder and the model id to store embeddings under, or None to skip.
    """
    default_model = collection_embedding_model_resolver.get_default_model_by_collection_id(
        session=session, collection_id=collection_id
    )
    space_key = None if default_model is None else default_model.name

    embedder = select_embedder(embedder_registry.get_registry(), space_key)
    if embedder is None:
        logger.warning("No embedding model loaded. Skipping embedding generation.")
        return None

    if default_model is not None:
        return embedder, default_model.embedding_model_id
    model_id = _register_default_model(
        session=session, collection_id=collection_id, embedder=embedder
    )
    return embedder, model_id


def _register_default_model(session: Session, collection_id: UUID, embedder: Embedder) -> UUID:
    """Register the embedder's space as the collection's default model and return its id.

    Gets or creates the embedding model for the embedder's space in the collection's
    dataset, links it to the collection, and marks it the default.

    Raises:
        ValueError: If the collection does not exist.
    """
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None:
        raise ValueError("Provided collection_id could not be found.")

    spec = embedder.embedding_space_spec()
    db_model = embedding_model_resolver.get_or_create(
        session=session,
        embedding_model=EmbeddingModelCreate(
            name=spec.space_key,
            embedding_dimension=spec.dimension,
            dataset_id=collection.dataset_id,
        ),
    )
    model_id = db_model.embedding_model_id
    collection_embedding_model_resolver.get_or_add_collection_model(
        session=session, collection_id=collection_id, embedding_model_id=model_id
    )
    collection_embedding_model_resolver.set_default(
        session=session, collection_id=collection_id, embedding_model_id=model_id
    )
    return model_id
