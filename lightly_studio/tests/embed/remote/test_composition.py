from __future__ import annotations

import re

import pytest
from lightly_studio_serve.embedder import (
    Capability,
    Embedder,
    ImageBytesEmbedder,
    TextEmbedder,
    VideoBytesEmbedder,
)
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec

from lightly_studio.embed.remote import composition
from lightly_studio.embed.remote.errors import RemoteEmbedderCapabilityError


class _Base(Embedder):
    """Stands for the class that carries what every capability shares."""

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key="acme/model@v1", dimension=2)


class _TextRoute(_Base, TextEmbedder):
    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        raise NotImplementedError


class _ImageBytesRoute(_Base, ImageBytesEmbedder):
    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        raise NotImplementedError


class _VideoBytesRoute(_Base, VideoBytesEmbedder):
    def embed_video_bytes(self, videos: list[bytes]) -> EmbeddingResult:
        raise NotImplementedError


# The order of this mapping is the order of the composed bases.
_CAPABILITY_TO_BASE: dict[Capability, type[Embedder]] = {
    Capability.TEXT: _TextRoute,
    Capability.IMAGE_BYTES: _ImageBytesRoute,
    Capability.VIDEO_BYTES: _VideoBytesRoute,
}


def test_compose_remote_embedder_class() -> None:
    built = composition.compose_remote_embedder_class(
        capabilities=[Capability.TEXT], capability_to_base=_CAPABILITY_TO_BASE
    )

    assert built.__name__ == "RemoteTextEmbedder"
    assert issubclass(built, TextEmbedder)
    assert not issubclass(built, ImageBytesEmbedder)


def test_compose_remote_embedder_class__several_capabilities() -> None:
    built = composition.compose_remote_embedder_class(
        capabilities=[Capability.TEXT, Capability.IMAGE_BYTES],
        capability_to_base=_CAPABILITY_TO_BASE,
    )

    assert built.__name__ == "RemoteTextImageBytesEmbedder"
    # Nothing abstract is left, so the class is instantiable.
    assert isinstance(built(), TextEmbedder)
    assert isinstance(built(), ImageBytesEmbedder)


def test_compose_remote_embedder_class__ignores_unroutable_capability() -> None:
    # `image_path` is a legal wire capability that no client of version 1 requests.
    built = composition.compose_remote_embedder_class(
        capabilities=[Capability.TEXT, Capability.IMAGE_PATH],
        capability_to_base=_CAPABILITY_TO_BASE,
    )

    assert built.__name__ == "RemoteTextEmbedder"


def test_compose_remote_embedder_class__reused() -> None:
    first = composition.compose_remote_embedder_class(
        capabilities=[Capability.TEXT], capability_to_base=_CAPABILITY_TO_BASE
    )
    second = composition.compose_remote_embedder_class(
        capabilities=[Capability.TEXT], capability_to_base=_CAPABILITY_TO_BASE
    )

    assert first is second


def test_compose_remote_embedder_class__nothing_routable() -> None:
    with pytest.raises(
        RemoteEmbedderCapabilityError, match=re.escape("routes to text, image_bytes, video_bytes")
    ):
        composition.compose_remote_embedder_class(
            capabilities=[Capability.IMAGE_PATH], capability_to_base=_CAPABILITY_TO_BASE
        )


def test_compose_remote_embedder_class__nothing_resolvable() -> None:
    # Nothing in LightlyStudio resolves a video-bytes embedder yet, so the error has to
    # name that rather than let `EmbedderRegistry.register` report the symptom.
    with pytest.raises(
        RemoteEmbedderCapabilityError,
        match=re.escape("EmbedderRegistry resolves text, image_bytes"),
    ):
        composition.compose_remote_embedder_class(
            capabilities=[Capability.VIDEO_BYTES], capability_to_base=_CAPABILITY_TO_BASE
        )


def test_compose_remote_embedder_class__repeated_capability() -> None:
    # `DescribeResponse.capabilities` is a list and validates no uniqueness, so a message
    # names each capability once.
    with pytest.raises(RemoteEmbedderCapabilityError, match=re.escape("advertises image_path.")):
        composition.compose_remote_embedder_class(
            capabilities=[Capability.IMAGE_PATH, Capability.IMAGE_PATH],
            capability_to_base=_CAPABILITY_TO_BASE,
        )
