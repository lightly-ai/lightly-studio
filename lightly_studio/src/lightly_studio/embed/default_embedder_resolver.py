"""Resolve collection defaults from the database and runtime embedder registry."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Literal, overload
from uuid import UUID

from sqlmodel import Session

from lightly_studio.embed.embedder import (
    Capability,
    Embedder,
    ImageBytesEmbedder,
    ImageCropPathEmbedder,
    ImagePathEmbedder,
    ImagePILEmbedder,
    TextEmbedder,
    VideoPathEmbedder,
)
from lightly_studio.embed.embedder_registry import EmbedderRegistry, _capabilities_of
from lightly_studio.models.embedding_model import EmbeddingModelCreate, EmbeddingModelTable
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


def _create_mobileclip() -> Embedder:
    from lightly_studio.embed.mobileclip_embedder import MobileCLIPEmbedder  # noqa: PLC0415

    return MobileCLIPEmbedder()


def _create_perception_encoder() -> Embedder:
    from lightly_studio.embed.perception_encoder_embedder import (  # noqa: PLC0415
        PerceptionEncoderEmbedder,
    )

    return PerceptionEncoderEmbedder()


_BUILTIN_SPACE_FACTORIES: dict[str, Callable[[], Embedder]] = {
    "mobileclip_s0": _create_mobileclip,
    "PE-Core-T16-384": _create_perception_encoder,
}
_BOOTSTRAP_SPACE_KEYS: dict[Capability, str] = {
    Capability.IMAGE_PATH: "mobileclip_s0",
    Capability.IMAGE_CROP_PATH: "mobileclip_s0",
    Capability.IMAGE_PIL: "mobileclip_s0",
    Capability.VIDEO_PATH: "PE-Core-T16-384",
}
_registry = EmbedderRegistry()


def register_embedder(embedder: Embedder, default_for: Iterable[Capability] | None = None) -> None:
    """Register a runtime provider and optionally select offline bootstrap defaults."""
    capabilities = set(_capabilities_of(embedder=embedder))
    selected = capabilities & _OFFLINE_CAPABILITIES if default_for is None else set(default_for)
    invalid = selected - capabilities
    if invalid:
        raise ValueError(
            f"Embedder does not implement capabilities: {_format_capabilities(invalid)}."
        )
    online = selected - _OFFLINE_CAPABILITIES
    if online:
        raise ValueError(f"Capabilities cannot bootstrap: {_format_capabilities(online)}.")

    _registry.register(embedder=embedder)
    space_key = embedder.embedding_space_spec().space_key
    for capability in selected:
        _BOOTSTRAP_SPACE_KEYS[capability] = space_key


@overload
def resolve(
    session: Session, collection_id: UUID, capability: Literal[Capability.IMAGE_PATH]
) -> tuple[ImagePathEmbedder, EmbeddingModelTable]: ...
@overload
def resolve(
    session: Session, collection_id: UUID, capability: Literal[Capability.IMAGE_CROP_PATH]
) -> tuple[ImageCropPathEmbedder, EmbeddingModelTable]: ...
@overload
def resolve(
    session: Session, collection_id: UUID, capability: Literal[Capability.VIDEO_PATH]
) -> tuple[VideoPathEmbedder, EmbeddingModelTable]: ...
@overload
def resolve(
    session: Session, collection_id: UUID, capability: Literal[Capability.IMAGE_PIL]
) -> tuple[ImagePILEmbedder, EmbeddingModelTable]: ...
@overload
def resolve(
    session: Session, collection_id: UUID, capability: Literal[Capability.TEXT]
) -> tuple[TextEmbedder, EmbeddingModelTable]: ...
@overload
def resolve(
    session: Session, collection_id: UUID, capability: Literal[Capability.IMAGE_BYTES]
) -> tuple[ImageBytesEmbedder, EmbeddingModelTable]: ...
def resolve(
    session: Session, collection_id: UUID, capability: Capability
) -> tuple[Embedder, EmbeddingModelTable]:
    """Resolve an existing persisted default and require the requested capability."""
    return _resolve(session=session, collection_id=collection_id, capability=capability)


@overload
def resolve_or_bootstrap(
    session: Session, collection_id: UUID, capability: Literal[Capability.IMAGE_PATH]
) -> tuple[ImagePathEmbedder, EmbeddingModelTable]: ...
@overload
def resolve_or_bootstrap(
    session: Session, collection_id: UUID, capability: Literal[Capability.IMAGE_CROP_PATH]
) -> tuple[ImageCropPathEmbedder, EmbeddingModelTable]: ...
@overload
def resolve_or_bootstrap(
    session: Session, collection_id: UUID, capability: Literal[Capability.VIDEO_PATH]
) -> tuple[VideoPathEmbedder, EmbeddingModelTable]: ...
@overload
def resolve_or_bootstrap(
    session: Session, collection_id: UUID, capability: Literal[Capability.IMAGE_PIL]
) -> tuple[ImagePILEmbedder, EmbeddingModelTable]: ...
@overload
def resolve_or_bootstrap(
    session: Session, collection_id: UUID, capability: Literal[Capability.TEXT]
) -> tuple[TextEmbedder, EmbeddingModelTable]: ...
@overload
def resolve_or_bootstrap(
    session: Session, collection_id: UUID, capability: Literal[Capability.IMAGE_BYTES]
) -> tuple[ImageBytesEmbedder, EmbeddingModelTable]: ...
def resolve_or_bootstrap(
    session: Session, collection_id: UUID, capability: Capability
) -> tuple[Embedder, EmbeddingModelTable]:
    """Resolve the persisted default, or create one from an offline bootstrap default."""
    if collection_embedding_model_resolver.has_default_by_collection_id(
        session=session, collection_id=collection_id
    ):
        return _resolve(session=session, collection_id=collection_id, capability=capability)
    space_key = _BOOTSTRAP_SPACE_KEYS.get(capability)
    if space_key is None:
        raise ValueError(f"No bootstrap embedder is configured for {capability.value}.")
    embedder = _registry.get(space_key) or _load_builtin(space_key)
    if embedder is None or capability not in _capabilities_of(embedder=embedder):
        raise ValueError(f"No usable bootstrap embedder is available for {capability.value}.")
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None:
        raise ValueError("Provided collection_id could not be found.")
    spec = embedder.embedding_space_spec()
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
    return embedder, model


def reset() -> None:
    """Reset process state to built-in defaults. Intended for test isolation."""
    _registry.clear()
    _BOOTSTRAP_SPACE_KEYS.clear()
    _BOOTSTRAP_SPACE_KEYS.update(
        {
            Capability.IMAGE_PATH: "mobileclip_s0",
            Capability.IMAGE_CROP_PATH: "mobileclip_s0",
            Capability.IMAGE_PIL: "mobileclip_s0",
            Capability.VIDEO_PATH: "PE-Core-T16-384",
        }
    )


def _resolve(
    session: Session, collection_id: UUID, capability: Capability
) -> tuple[Embedder, EmbeddingModelTable]:
    model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=session, collection_id=collection_id
    )
    if model_id is None:
        raise ValueError(f"Collection {collection_id} has no default embedding model.")
    model = embedding_model_resolver.get_by_id(session=session, embedding_model_id=model_id)
    if model is None:
        raise ValueError(f"Default embedding model {model_id} could not be found.")
    embedder = _registry.get(model.name) or _load_builtin(model.name)
    if embedder is None:
        raise ValueError(f"No embedder is registered for embedding space {model.name!r}.")
    _validate_spec(embedder=embedder, model=model)
    if capability not in _capabilities_of(embedder=embedder):
        raise ValueError(f"Embedding space {model.name!r} does not support {capability.value}.")
    return embedder, model


def _load_builtin(space_key: str) -> Embedder | None:
    factory = _BUILTIN_SPACE_FACTORIES.get(space_key)
    if factory is None:
        return None
    embedder = factory()
    _registry.register(embedder=embedder)
    return embedder


def _validate_spec(embedder: Embedder, model: EmbeddingModelTable) -> None:
    spec = embedder.embedding_space_spec()
    if spec.space_key != model.name or spec.dimension != model.embedding_dimension:
        raise ValueError(
            f"Registered embedder spec {spec} conflicts with persisted embedding space "
            f"{model.name!r} ({model.embedding_dimension})."
        )


def _format_capabilities(capabilities: set[Capability]) -> str:
    return ", ".join(sorted(capability.value for capability in capabilities))
