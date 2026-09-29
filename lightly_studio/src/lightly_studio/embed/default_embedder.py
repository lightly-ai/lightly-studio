"""Resolve the embedder and model id an embed function should use for a collection."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from lightly_studio_serve.embedder import Embedder
from sqlmodel import Session

from lightly_studio.embed import embedder_config, embedder_registry
from lightly_studio.embed.embedder_config import EmbedderConfig
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.errors import (
    MissingCapabilityError,
    NoDefaultEmbeddingModelError,
    RemoteEmbedderUnavailableError,
)
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
) -> tuple[_EmbedderT, UUID] | None:
    """Resolve the embedder and model id an embed function should use, or None to skip.

    Follows the pattern every ``embed_*`` function shares. ``get_embedder_fn`` picks the
    capability the caller needs (image, text, ...) from the registry:

    - The collection has a default model in the DB: its embedding space selects the embedder.
    - The collection has no default in the DB yet: the registry's bootstrap embedder is used and
      registered as the collection's default.

    Logs a warning and returns None when the registry has no matching embedder, so the
    caller only needs to return on None.

    Args:
        session: Database session for resolver operations.
        collection_id: The collection whose default embedding model is used. Expected to
            exist; only validated when a bootstrap model is registered.
        get_embedder_fn: The typed getter of the needed capability. It takes the registry, the
            space key (None for the capability's bootstrap space) and the stored
            configuration of that space (None when there is none).

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


def check_embedder_dimension(
    session: Session,
    collection_id: UUID,
    get_embedder_fn: Callable[
        [EmbedderRegistry, str | None, EmbedderConfig | None], Embedder | None
    ],
) -> None:
    """Check the embedder that will embed the collection against the stored dimension.

    ``resolve_default_embedder`` makes the same check, but only when the samples are already
    stored. Call this before storing them, so that a mismatch stores no sample. The registry
    caches the embedder, so the embedding after the insert does not build it again.

    A collection with a default model checks the embedder of that model. A collection
    without one checks the registry's bootstrap embedder against the dataset's model of the
    same space. A space without an embedder passes.

    Args:
        session: Database session for resolver operations.
        collection_id: The collection whose embedder is checked.
        get_embedder_fn: The typed getter of the needed capability, as described in
            ``resolve_default_embedder``.

    Raises:
        ValueError: If the embedder's dimension does not match the stored dimension of its
            space (a wrongly registered embedder), or if the collection does not exist.
    """
    default_model = collection_embedding_model_resolver.get_default_model_by_collection_id(
        session=session, collection_id=collection_id
    )
    if default_model is not None:
        _embedder_for_model(default_model=default_model, get_embedder_fn=get_embedder_fn)
        return
    _check_bootstrap_dimension(
        session=session, collection_id=collection_id, get_embedder_fn=get_embedder_fn
    )


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
    _check_dimension(
        embedder_dimension=embedder.embedding_space_spec().dimension,
        stored_dimension=default_model.embedding_dimension,
        space_key=default_model.name,
    )
    return embedder


def _check_bootstrap_dimension(
    session: Session,
    collection_id: UUID,
    get_embedder_fn: Callable[
        [EmbedderRegistry, str | None, EmbedderConfig | None], Embedder | None
    ],
) -> None:
    """Check the bootstrap embedder against the dataset's model of its space, if there is one.

    ``_register_default_model`` makes the same check in ``get_or_create``. A dataset without
    an embedding model passes before the embedder is resolved, so a first import loads no
    model before its samples are stored.

    Raises:
        ValueError: If the collection does not exist, or if the dataset has a model for the
            embedder's space with another dimension.
    """
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None:
        raise ValueError("Provided collection_id could not be found.")
    dataset_models = embedding_model_resolver.get_all_by_dataset_id(
        session=session, dataset_id=collection.dataset_id
    )
    if not dataset_models:
        return
    embedder = get_embedder_fn(embedder_registry.get_registry(), None, None)
    if embedder is None:
        return
    spec = embedder.embedding_space_spec()
    for model in dataset_models:
        if model.name == spec.space_key:
            _check_dimension(
                embedder_dimension=spec.dimension,
                stored_dimension=model.embedding_dimension,
                space_key=model.name,
            )


def _check_dimension(embedder_dimension: int, stored_dimension: int, space_key: str) -> None:
    """Check the dimension of an embedder against the stored dimension of its space.

    Args:
        embedder_dimension: The dimension that the embedder produces.
        stored_dimension: The dimension that the dataset stores for the space.
        space_key: The embedding space, named in the error.

    Raises:
        ValueError: If the dimensions differ (a wrongly registered embedder).
    """
    if embedder_dimension != stored_dimension:
        raise ValueError(
            f"Embedder dimension {embedder_dimension} does not match the dimension "
            f"{stored_dimension} stored for space '{space_key}'. "
            "A wrongly registered embedder is likely."
        )


def _register_default_model(session: Session, collection_id: UUID, embedder: Embedder) -> UUID:
    """Register the embedder's space as the collection's default model and return its id.

    Gets or creates the embedding model for the embedder's space in the collection's
    dataset, links it to the collection, and marks it the default.

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
    collection_embedding_model_resolver.get_or_add_collection_model(
        session=session, collection_id=collection_id, embedding_model_id=model_id
    )
    collection_embedding_model_resolver.set_default(
        session=session, collection_id=collection_id, embedding_model_id=model_id
    )
    return model_id
