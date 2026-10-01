"""Resolve the embedder and model id an embed function should use for a collection."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from lightly_studio_serve.embedder import Capability, Embedder
from sqlmodel import Session

from lightly_studio.embed import embedder_config, embedder_registry
from lightly_studio.embed.embedder_config import EmbedderConfig
from lightly_studio.embed.embedder_registry import EmbedderRegistry
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
    get_embedder_fn: Callable[
        [EmbedderRegistry, str | None, EmbedderConfig | None], _EmbedderT | None
    ],
    capability: Capability | None = None,
) -> tuple[_EmbedderT, UUID] | None:
    """Resolve the embedder and model id an embed function should use, or None to skip.

    Follows the pattern every ``embed_*`` function shares. ``get_embedder_fn`` picks the
    capability the caller needs (image, text, ...) from the registry:

    - The collection has a default model in the DB: its embedding space selects the embedder.
    - The collection has no default in the DB yet, and its parent collection has a default
      model that stores a server: that model becomes the collection's default. This applies
      only if the caller gives ``capability`` and no registration set the bootstrap space of
      ``capability``. Thus crops and frames that a later process adds use the server of
      their parent.
    - Else: the registry's bootstrap embedder is used and registered as the collection's
      default. The model stores the server of an embedder that names one, see
      ``PersistableEmbedder``.

    Logs a warning and returns None when the registry has no matching embedder, so the
    caller only needs to return on None.

    Args:
        session: Database session for resolver operations.
        collection_id: The collection whose default embedding model is used. Expected to
            exist; only validated when a bootstrap model is registered.
        get_embedder_fn: The typed getter of the needed capability. It takes the registry, the
            space key (None for the capability's bootstrap space) and the stored
            configuration of that space (None when there is none).
        capability: The capability of ``get_embedder_fn``. Give it to let a collection
            without a default model take the server of its parent. None disables this.

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
        embedder = _embedder_for_model(default_model=default_model, get_embedder_fn=get_embedder_fn)
        if embedder is None:
            logger.warning("No embedding model loaded. Skipping embedding generation.")
            return None
        return embedder, default_model.embedding_model_id

    parent_model = _parent_server_model(
        session=session, collection_id=collection_id, capability=capability
    )
    if parent_model is not None:
        return _resolve_from_parent(
            session=session,
            collection_id=collection_id,
            parent_model=parent_model,
            get_embedder_fn=get_embedder_fn,
        )

    embedder = get_embedder_fn(embedder_registry.get_registry(), None, None)
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
    get_embedder_fn: Callable[
        [EmbedderRegistry, str | None, EmbedderConfig | None], _EmbedderT | None
    ],
    query_kind: str,
) -> _EmbedderT:
    """Resolve the embedder for an interactive query, without mutating the collection.

    Unlike ``resolve_default_embedder``, this never bootstraps a default model and raises
    (rather than skipping) when the collection has no default model, since an interactive
    query must not mutate the collection. The registry still bootstraps the embedder for the
    default model's space through ``get_embedder_fn``.

    Args:
        session: Database session for resolver operations.
        collection_id: The collection whose default embedding model is used.
        get_embedder_fn: The typed getter of the needed capability, as described in
            ``resolve_default_embedder``.
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

    embedder = _embedder_for_model(default_model=default_model, get_embedder_fn=get_embedder_fn)
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
    get_embedder_fn: Callable[
        [EmbedderRegistry, str | None, EmbedderConfig | None], _EmbedderT | None
    ],
) -> _EmbedderT | None:
    """Resolve and dimension-check the embedder of an existing default model.

    The model row carries the configuration of its space, so a space that no embedder is
    registered for resolves to the backend the row names.

    Args:
        default_model: The collection's default embedding model.
        get_embedder_fn: The typed getter of the needed capability, as described in
            ``resolve_default_embedder``.

    Returns:
        The embedder for the model's space, or None if no source has a matching embedder.

    Raises:
        ValueError: If the embedder's dimension does not match the model's stored dimension
            (a wrongly registered embedder).
    """
    config = embedder_config.from_embedding_model(embedding_model=default_model)
    embedder = get_embedder_fn(embedder_registry.get_registry(), default_model.name, config)
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


def _resolve_from_parent(
    session: Session,
    collection_id: UUID,
    parent_model: EmbeddingModelTable,
    get_embedder_fn: Callable[
        [EmbedderRegistry, str | None, EmbedderConfig | None], _EmbedderT | None
    ],
) -> tuple[_EmbedderT, UUID] | None:
    """Make the model of the parent collection the default of the collection.

    If the server of the model cannot give the embedder, the collection gets no default
    model, so that a later call tries the server again. A bootstrap default would put the
    collection in another embedding space than its parent.

    Args:
        session: Database session for resolver operations.
        collection_id: The collection that has no default model.
        parent_model: The default model of the parent collection. It stores a server.
        get_embedder_fn: The typed getter of the needed capability, as described in
            ``resolve_default_embedder``.

    Returns:
        The embedder and the model id to store embeddings under, or None to skip.
    """
    embedder = _embedder_for_model(default_model=parent_model, get_embedder_fn=get_embedder_fn)
    if embedder is None:
        logger.warning(
            "Cannot embed the collection %s on the server %s of its parent collection for "
            "space %r. Skipping embedding generation.",
            collection_id,
            parent_model.remote_embedder_url,
            parent_model.name,
        )
        return None
    model_id = _register_default_model(
        session=session, collection_id=collection_id, embedder=embedder
    )
    return embedder, model_id


def _parent_server_model(
    session: Session, collection_id: UUID, capability: Capability | None
) -> EmbeddingModelTable | None:
    """Give the default model of the parent collection if the collection can take it.

    The collection can take it if ``capability`` is given, no registration set the
    bootstrap space of ``capability``, and the model stores a server.
    """
    if capability is None or embedder_registry.get_registry().is_bootstrap_registered(
        capability=capability
    ):
        return None
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None or collection.parent_collection_id is None:
        return None
    parent_model = collection_embedding_model_resolver.get_default_model_by_collection_id(
        session=session, collection_id=collection.parent_collection_id
    )
    if parent_model is None or parent_model.remote_embedder_url is None:
        return None
    return parent_model


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
