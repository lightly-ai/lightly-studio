"""Resolve a collection's default embedding space from the database.

Returns the collection's default embedding space as an ``EmbeddingSpaceSpec``. The
embedder that produces the space is a separate concern owned by ``embedder_registry``.
"""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlmodel import Session

from lightly_studio.embed import embedder_registry
from lightly_studio.embed.embedder import Capability, Embedder
from lightly_studio.embed.types import EmbeddingSpaceSpec
from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.resolvers import (
    collection_embedding_model_resolver,
    collection_resolver,
    embedding_model_resolver,
)

_OFFLINE_CAPABILITIES = frozenset(
    {
        Capability.IMAGE_PATH,
        Capability.IMAGE_CROP_PATH,
        Capability.VIDEO_PATH,
        Capability.IMAGE_PIL,
    }
)
_DEFAULT_BOOTSTRAP_SPACE_KEYS: dict[Capability, str] = {
    Capability.IMAGE_PATH: "mobileclip_s0",
    Capability.IMAGE_CROP_PATH: "mobileclip_s0",
    Capability.IMAGE_PIL: "mobileclip_s0",
    Capability.VIDEO_PATH: "PE-Core-T16-384",
}
_BOOTSTRAP_SPACE_KEYS: dict[Capability, str] = dict(_DEFAULT_BOOTSTRAP_SPACE_KEYS)


def register_embedder(embedder: Embedder, default_for: Iterable[Capability] | None = None) -> None:
    """Register a runtime provider and optionally select offline bootstrap defaults."""
    capabilities = set(embedder_registry.capabilities_of(embedder=embedder))
    selected = capabilities & _OFFLINE_CAPABILITIES if default_for is None else set(default_for)
    invalid = selected - capabilities
    if invalid:
        raise ValueError(
            f"Embedder does not implement capabilities: {_format_capabilities(invalid)}."
        )
    online = selected - _OFFLINE_CAPABILITIES
    if online:
        raise ValueError(f"Capabilities cannot bootstrap: {_format_capabilities(online)}.")

    embedder_registry.register(embedder=embedder)
    space_key = embedder.embedding_space_spec().space_key
    for capability in selected:
        _BOOTSTRAP_SPACE_KEYS[capability] = space_key


def resolve(session: Session, collection_id: UUID, capability: Capability) -> EmbeddingSpaceSpec:
    """Resolve the persisted default space, requiring an embedder for the capability."""
    return _resolve(session=session, collection_id=collection_id, capability=capability)


def resolve_or_bootstrap(
    session: Session, collection_id: UUID, capability: Capability
) -> EmbeddingSpaceSpec:
    """Resolve the persisted default space, or create one from an offline bootstrap default."""
    if collection_embedding_model_resolver.has_default_by_collection_id(
        session=session, collection_id=collection_id
    ):
        return _resolve(session=session, collection_id=collection_id, capability=capability)
    space_key = _BOOTSTRAP_SPACE_KEYS.get(capability)
    if space_key is None:
        raise ValueError(f"No bootstrap embedder is configured for {capability.value}.")
    if not embedder_registry.has_capability(space_key=space_key, capability=capability):
        raise ValueError(f"No usable bootstrap embedder is available for {capability.value}.")
    spec = embedder_registry.get_spec(space_key=space_key)
    assert spec is not None  # has_capability guarantees a loaded embedder for the space.
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None:
        raise ValueError("Provided collection_id could not be found.")
    model = embedding_model_resolver.get_or_create(
        session=session,
        embedding_model=EmbeddingModelCreate(
            name=spec.space_key,
            embedding_dimension=spec.dimension,
            dataset_id=collection.dataset_id,
        ),
    )
    collection_embedding_model_resolver.get_or_add_collection_model(
        session=session, collection_id=collection_id, embedding_model_id=model.embedding_model_id
    )
    collection_embedding_model_resolver.set_default(
        session=session, collection_id=collection_id, embedding_model_id=model.embedding_model_id
    )
    return spec


def reset() -> None:
    """Reset process state to built-in defaults. Intended for test isolation."""
    embedder_registry.clear()
    _BOOTSTRAP_SPACE_KEYS.clear()
    _BOOTSTRAP_SPACE_KEYS.update(_DEFAULT_BOOTSTRAP_SPACE_KEYS)


def _resolve(session: Session, collection_id: UUID, capability: Capability) -> EmbeddingSpaceSpec:
    model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=session, collection_id=collection_id
    )
    if model_id is None:
        raise ValueError(f"Collection {collection_id} has no default embedding model.")
    model = embedding_model_resolver.get_by_id(session=session, embedding_model_id=model_id)
    if model is None:
        raise ValueError(f"Default embedding model {model_id} could not be found.")
    registered_spec = embedder_registry.get_spec(space_key=model.name)
    if registered_spec is None:
        raise ValueError(f"No embedder is registered for embedding space {model.name!r}.")
    persisted_spec = EmbeddingSpaceSpec(space_key=model.name, dimension=model.embedding_dimension)
    if registered_spec != persisted_spec:
        raise ValueError(
            f"Registered embedder spec {registered_spec} conflicts with persisted embedding "
            f"space {model.name!r} ({model.embedding_dimension})."
        )
    if not embedder_registry.has_capability(space_key=model.name, capability=capability):
        raise ValueError(f"Embedding space {model.name!r} does not support {capability.value}.")
    return persisted_spec


def _format_capabilities(capabilities: set[Capability]) -> str:
    return ", ".join(sorted(capability.value for capability in capabilities))
