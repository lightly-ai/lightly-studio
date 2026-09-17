from __future__ import annotations

import pytest
from lightly_studio_serve.embedder import (
    Capability,
    Embedder,
    ImageBytesEmbedder,
    TextEmbedder,
)
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec

from lightly_studio.embed.remote import composition
from lightly_studio.embed.remote.errors import RemoteEmbedderCapabilityError

ROUTES_TO = [Capability.TEXT, Capability.IMAGE_BYTES, Capability.VIDEO_BYTES]
RESOLVABLE = [Capability.TEXT, Capability.IMAGE_BYTES]


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


def test_composed_class() -> None:
    built = composition.composed_class(bases=(_TextRoute,), name="RemoteTextEmbedder")

    assert built.__name__ == "RemoteTextEmbedder"
    assert issubclass(built, TextEmbedder)
    assert not issubclass(built, ImageBytesEmbedder)


def test_composed_class__several_capabilities() -> None:
    built = composition.composed_class(
        bases=(_TextRoute, _ImageBytesRoute), name="RemoteTextImageBytesEmbedder"
    )

    # Nothing abstract is left, so the class is instantiable.
    assert isinstance(built(), TextEmbedder)
    assert isinstance(built(), ImageBytesEmbedder)


def test_composed_class__reused() -> None:
    first = composition.composed_class(bases=(_TextRoute,), name="RemoteTextEmbedder")
    second = composition.composed_class(bases=(_TextRoute,), name="RemoteTextEmbedder")

    assert first is second


def test_check_routable() -> None:
    composition.check_routable(
        advertised=[Capability.TEXT],
        routable=[Capability.TEXT],
        routes_to=ROUTES_TO,
        resolvable=RESOLVABLE,
    )


def test_check_routable__nothing_routable() -> None:
    # `image_path` is a legal wire capability that no client of version 1 requests.
    with pytest.raises(RemoteEmbedderCapabilityError) as error:
        composition.check_routable(
            advertised=[Capability.IMAGE_PATH],
            routable=[],
            routes_to=ROUTES_TO,
            resolvable=RESOLVABLE,
        )

    assert "routes to text, image_bytes, video_bytes" in str(error.value)


def test_check_routable__nothing_resolvable() -> None:
    # Nothing in LightlyStudio resolves a video-bytes embedder yet, so the error has to
    # name that rather than let `EmbedderRegistry.register` report the symptom.
    with pytest.raises(RemoteEmbedderCapabilityError) as error:
        composition.check_routable(
            advertised=[Capability.VIDEO_BYTES],
            routable=[Capability.VIDEO_BYTES],
            routes_to=ROUTES_TO,
            resolvable=RESOLVABLE,
        )

    assert "EmbedderRegistry resolves text, image_bytes" in str(error.value)


def test_names() -> None:
    assert composition.names(capabilities=[Capability.TEXT, Capability.IMAGE_BYTES]) == (
        "text, image_bytes"
    )


def test_names__repeated() -> None:
    # `DescribeResponse.capabilities` is a list and validates no uniqueness.
    assert composition.names(capabilities=[Capability.TEXT, Capability.TEXT]) == "text"
