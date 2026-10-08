"""Resolve the embedder and model id an embed function should use for a collection."""

from __future__ import annotations

import logging
from typing import TypeVar
from uuid import UUID

from lightly_studio_serve.embedder import Embedder
from sqlmodel import Session

from lightly_studio.embed import embedder_config, embedder_registry
from lightly_studio.embed.errors import (
    MissingCapabilityError,
    NoDefaultEmbeddingModelError,
    RemoteEmbedderUnavailableError,
)
from lightly_studio.embed.remote.endpoint import PersistableEmbedder
from lightly_studio.models.embedding_model import EmbeddingModelCreate, EmbeddingModelTable
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
    embedder_type: type[_EmbedderT],
) -> tuple[_EmbedderT, UUID] | None:
    """Resolve the embedder and model id an embed function should use, or None to skip.

    Follows the pattern every ``embed_*`` function shares. ``embedder_type`` picks the
    capability the caller needs (image, text, ...) from the registry:

    - The collection has a default model in the DB: its embedding space selects the embedder.
    - The collection has no default in the DB yet: the registry's bootstrap embedder is used and
      registered as the collection's default. The model stores the server of an embedder that
      names one, see ``PersistableEmbedder``.

    Logs a warning and returns None when the registry has no matching embedder, so the
    caller only needs to return on None.

    Args:
        session: Database session for resolver operations.
        collection_id: The collection whose default embedding model is used. Expected to
            exist; only validated when a bootstrap model is registered.
        embedder_type: The embedder interface of the needed capability, such as
            ``ImagePathEmbedder``.

    Returns:
        The embedder and the model id to store embeddings under, or None to skip.

    Raises:
        ValueError: If the embedder's dimension does not match the space's stored dimension
            (a wrongly registered embedder), or if the collection does not exist.
    """
    # TODO(Michal, 09/2026): Raise an exception instead of logging a warning and returning
    # None when no embedder is loaded, and handle it upstream in the callers.
    default_model = collection_embedding_model_resolver.get_default_model_by_collection_id(
        session=session, collection_id=collection_id
    )
    if default_model is not None:
        embedder = _embedder_for_model(default_model=default_model, embedder_type=embedder_type)
        if embedder is None:
            logger.warning("No embedding model loaded. Skipping embedding generation.")
            return None
        return embedder, default_model.embedding_model_id

    embedder = embedder_registry.get_registry().get_embedder(embedder_type=embedder_type)
    if embedder is None:
        logger.warning("No embedding model loaded. Skipping embedding generation.")
        return None
    model_id = _register_default_model(
        session=session, collection_id=collection_id, embedder=embedder
    )
    return embedder, model_id


def resolve_query_embedder(
    session: Session,
    collection_id: UUID,
    embedder_type: type[_EmbedderT],
    query_kind: str,
) -> _EmbedderT:
    """Resolve the embedder for an interactive query, without mutating the collection.

    Unlike ``resolve_default_embedder``, this never bootstraps a default model and raises
    (rather than skipping) when the collection has no default model, since an interactive
    query must not mutate the collection. The registry still bootstraps the embedder for the
    default model's space.

    Args:
        session: Database session for resolver operations.
        collection_id: The collection whose default embedding model is used.
        embedder_type: The embedder interface of the needed capability, such as
            ``TextEmbedder``.
        query_kind: What the query embeds, such as "text" or "images". Used in errors.

    Returns:
        The embedder for the collection's default embedding space.

    Raises:
        NoDefaultEmbeddingModelError: If the collection has no default embedding model.
        RemoteEmbedderUnavailableError: If the embedding server of the space cannot be used.
        MissingCapabilityError: If no embedder of the space has the needed capability.
        ValueError: If the embedder's dimension does not match the space's stored dimension
            (a wrongly registered embedder).
    """
    default_model = collection_embedding_model_resolver.get_default_model_by_collection_id(
        session=session, collection_id=collection_id
    )
    if default_model is None:
        raise NoDefaultEmbeddingModelError("The collection has no default embedding model.")

    embedder = _embedder_for_model(default_model=default_model, embedder_type=embedder_type)
    if embedder is not None:
        return embedder
    config = embedder_config.from_embedding_model(embedding_model=default_model)
    if config.url is not None and embedder_registry.get_registry().is_remote_unavailable(
        config=config
    ):
        raise RemoteEmbedderUnavailableError(space_key=default_model.name, url=config.url)
    raise MissingCapabilityError(space_key=default_model.name, query_kind=query_kind)


def _embedder_for_model(
    default_model: EmbeddingModelTable,
    embedder_type: type[_EmbedderT],
) -> _EmbedderT | None:
    """Resolve and dimension-check the embedder of an existing default model.

    The model row carries the configuration of its space, so a space that no embedder is
    registered for resolves to the backend the row names.

    Args:
        default_model: The collection's default embedding model.
        embedder_type: The embedder interface of the needed capability, such as
            ``TextEmbedder``.

    Returns:
        The embedder for the model's space, or None if no source has a matching embedder.

    Raises:
        ValueError: If the embedder's dimension does not match the model's stored dimension
            (a wrongly registered embedder).
    """
    config = embedder_config.from_embedding_model(embedding_model=default_model)
    embedder = embedder_registry.get_registry().get_embedder(
        embedder_type=embedder_type, space_key=default_model.name, config=config
    )
    if embedder is None:
        return None
    spec = embedder.embedding_space_spec()
    if spec.dimension != default_model.embedding_dimension:
        raise ValueError(
            f"Embedder dimension {spec.dimension} does not match the collection's default "
            f"model dimension {default_model.embedding_dimension} for space "
            f"'{default_model.name}'. A wrongly registered embedder is likely."
        )
    return embedder


def _register_default_model(session: Session, collection_id: UUID, embedder: Embedder) -> UUID:
    """Register the embedder's space as the collection's default model and return its id.

    Gets or creates the embedding model for the embedder's space in the collection's
    dataset, stores the server of the embedder on it, links it to the collection, and marks
    it the default.

    Raises:
        ValueError: If the collection does not exist, or if the dataset already has a model
            for the embedder's space with a different dimension (a wrongly registered embedder).
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
    _store_remote_endpoint(session=session, embedding_model=db_model, embedder=embedder)
    collection_embedding_model_resolver.get_or_add_collection_model(
        session=session, collection_id=collection_id, embedding_model_id=model_id
    )
    collection_embedding_model_resolver.set_default(
        session=session, collection_id=collection_id, embedding_model_id=model_id
    )
    return model_id


def _store_remote_endpoint(
    session: Session, embedding_model: EmbeddingModelTable, embedder: Embedder
) -> None:
    """Store the server of the embedder on the model, so that a later process reaches it.

    The model keeps the URL and the API key in plain text, the same write that
    ``register_remote_embedder`` makes. An embedder that names no server leaves the model
    unchanged, so a local embedder does not clear a server that the model already stores. A
    model that already stores a server keeps it, so that only ``register_remote_embedder``
    changes it.
    """
    if embedding_model.remote_embedder_url is not None:
        return
    if not isinstance(embedder, PersistableEmbedder):
        return
    endpoint = embedder.remote_endpoint()
    if endpoint is None:
        return
    embedding_model_resolver.set_remote_embedder(
        session=session,
        embedding_model_id=embedding_model.embedding_model_id,
        url=endpoint.url,
        api_key=endpoint.api_key,
    )
