from __future__ import annotations

import logging

import numpy as np
import pytest
from pytest_mock import MockerFixture

from lightly_studio.embed import embedder_registry
from lightly_studio.embed.embedder import (
    Capability,
    Embedder,
    ImagePathEmbedder,
    TextEmbedder,
    VideoPathEmbedder,
)
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.types import EmbeddingResult, EmbeddingSpaceSpec


def _result(dimension: int, count: int) -> EmbeddingResult:
    return EmbeddingResult(
        embeddings=np.zeros((count, dimension), dtype=np.float32),
        kept_indices=list(range(count)),
    )


class _FakeTextImageEmbedder(TextEmbedder, ImagePathEmbedder):
    def __init__(self, space_key: str, dimension: int = 2) -> None:
        self._space_key = space_key
        self._dimension = dimension

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=self._space_key, dimension=self._dimension)

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        return _result(self._dimension, len(texts))

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        return _result(self._dimension, len(paths))


class _FakeVideoEmbedder(VideoPathEmbedder):
    def __init__(self, space_key: str, dimension: int = 2) -> None:
        self._space_key = space_key
        self._dimension = dimension

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=self._space_key, dimension=self._dimension)

    def embed_videos(self, paths: list[str]) -> EmbeddingResult:
        return _result(self._dimension, len(paths))


class _FakeImagePathEmbedder(ImagePathEmbedder):
    def __init__(self, space_key: str, dimension: int = 2) -> None:
        self._space_key = space_key
        self._dimension = dimension

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=self._space_key, dimension=self._dimension)

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        return _result(self._dimension, len(paths))


class _FakeNoCapabilityEmbedder(Embedder):
    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key="none", dimension=2)


class TestEmbedderRegistryRegister:
    def test_register(self) -> None:
        registry = EmbedderRegistry()
        embedder = _FakeTextImageEmbedder(space_key="space-a")

        registry.register(embedder=embedder)

        # Getters for implemented capabilities return the embedder.
        assert registry.get_text_embedder(space_key="space-a") is embedder
        assert registry.get_image_path_embedder(space_key="space-a") is embedder
        # Getters for capabilities the embedder lacks return None.
        assert registry.get_image_crop_path_embedder(space_key="space-a") is None
        assert registry.get_video_path_embedder(space_key="space-a") is None
        assert registry.get_image_pil_embedder(space_key="space-a") is None
        assert registry.get_image_bytes_embedder(space_key="space-a") is None

    def test_register__no_capability(self) -> None:
        registry = EmbedderRegistry()

        with pytest.raises(ValueError, match="no capability"):
            registry.register(embedder=_FakeNoCapabilityEmbedder())

    def test_register__replaces_existing(self, caplog: pytest.LogCaptureFixture) -> None:
        registry = EmbedderRegistry()
        first = _FakeTextImageEmbedder(space_key="space-a")
        second = _FakeTextImageEmbedder(space_key="space-a")

        registry.register(embedder=first)
        with caplog.at_level(logging.WARNING):
            registry.register(embedder=second)

        assert registry.get_text_embedder(space_key="space-a") is second
        assert "Replacing embedder" in caplog.text

    def test_register__conflicting_spec_raises(self) -> None:
        registry = EmbedderRegistry()
        first = _FakeTextImageEmbedder(space_key="space-a", dimension=2)
        registry.register(embedder=first)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(embedder=_FakeTextImageEmbedder(space_key="space-a", dimension=3))

        # The registry is unchanged after the rejected replacement.
        assert registry.get_text_embedder(space_key="space-a") is first

    def test_register__separate_spaces(self) -> None:
        registry = EmbedderRegistry()
        embedder_a = _FakeTextImageEmbedder(space_key="space-a")
        embedder_b = _FakeTextImageEmbedder(space_key="space-b")

        registry.register(embedder=embedder_a)
        registry.register(embedder=embedder_b)

        assert registry.get_text_embedder(space_key="space-a") is embedder_a
        assert registry.get_text_embedder(space_key="space-b") is embedder_b


class TestEmbedderRegistryBootstrapFor:
    def test_none_sets_defaults_for_all_capabilities(self) -> None:
        registry = EmbedderRegistry()
        embedder = _FakeTextImageEmbedder(space_key="space-a")

        registry.register(embedder=embedder, bootstrap_for=None)

        # TEXT has no built-in default, so registering with None makes this the default.
        assert registry.get_text_embedder() is embedder
        assert registry.get_image_path_embedder() is embedder

    def test_empty_set_changes_no_defaults(self) -> None:
        registry = EmbedderRegistry()
        embedder = _FakeTextImageEmbedder(space_key="space-a")

        registry.register(embedder=embedder, bootstrap_for=set())

        # TEXT still has no default; the embedder did not become one.
        assert registry.get_text_embedder() is None

    def test_explicit_set_updates_only_requested(self) -> None:
        registry = EmbedderRegistry()
        embedder = _FakeTextImageEmbedder(space_key="space-a")

        registry.register(embedder=embedder, bootstrap_for={Capability.TEXT})

        assert registry.get_text_embedder() is embedder
        # IMAGE_PATH was not requested, so its default is unchanged (still mobileclip).
        assert registry.get_image_path_embedder() is not embedder

    def test_explicit_set_ignores_unsupported_capability(self) -> None:
        registry = EmbedderRegistry()
        embedder = _FakeTextImageEmbedder(space_key="space-a")

        # VIDEO_PATH is not implemented by this embedder, so it is ignored.
        registry.register(embedder=embedder, bootstrap_for={Capability.TEXT, Capability.VIDEO_PATH})

        assert registry.get_text_embedder() is embedder
        # The video default was left pointing at its built-in space.
        assert registry.get_video_path_embedder(space_key="space-a") is None


class TestEmbedderRegistryBootstrapDefaults:
    def test_text_and_bytes_have_no_default(self) -> None:
        registry = EmbedderRegistry()

        assert registry.get_text_embedder() is None
        assert registry.get_image_bytes_embedder() is None
        assert registry.get_bootstrap_space(capability=Capability.TEXT) is None
        assert registry.get_bootstrap_space(capability=Capability.IMAGE_BYTES) is None

    def test_get_bootstrap_space_returns_custom_provider_spec(self) -> None:
        registry = EmbedderRegistry()
        embedder = _FakeTextImageEmbedder(space_key="space-a", dimension=7)

        registry.register(embedder=embedder, bootstrap_for={Capability.TEXT})

        spec = registry.get_bootstrap_space(capability=Capability.TEXT)
        assert spec == EmbeddingSpaceSpec(space_key="space-a", dimension=7)

    def test_get_bootstrap_space_none_when_default_lacks_capability(self) -> None:
        registry = EmbedderRegistry()
        # A partial provider registered under the mobileclip key that only embeds
        # text and images, not crops.
        partial = _FakeTextImageEmbedder(space_key="mobileclip_s0", dimension=512)
        registry.register(embedder=partial, bootstrap_for=set())

        # The IMAGE_CROP_PATH default points at mobileclip_s0, but the registered
        # provider there lacks that capability, so lookup returns None.
        assert registry.get_bootstrap_space(capability=Capability.IMAGE_CROP_PATH) is None


class TestEmbedderRegistryInstanceIsolation:
    def test_instances_have_independent_state(self) -> None:
        registry_a = EmbedderRegistry()
        registry_b = EmbedderRegistry()
        embedder = _FakeTextImageEmbedder(space_key="space-a")

        registry_a.register(embedder=embedder, bootstrap_for={Capability.TEXT})

        assert registry_a.get_text_embedder() is embedder
        assert registry_b.get_text_embedder() is None
        assert registry_b.get_text_embedder(space_key="space-a") is None


class TestEmbedderRegistryLookup:
    def test_explicit_key_does_not_fall_back(self) -> None:
        registry = EmbedderRegistry()

        # An unknown explicit key returns None even though a bootstrap default exists.
        assert registry.get_image_path_embedder(space_key="unknown") is None

    def test_unknown_key_returns_none(self, mocker: MockerFixture) -> None:
        registry = EmbedderRegistry()
        mocker.patch.object(embedder_registry, "_load_builtin_embedder", return_value=None)

        assert registry.get_video_path_embedder(space_key="unknown") is None


class TestEmbedderRegistryLazyLoading:
    def test_deferred_construction(self, mocker: MockerFixture) -> None:
        load = mocker.patch.object(embedder_registry, "_load_builtin_embedder", return_value=None)
        EmbedderRegistry()

        # Constructing the registry loads no built-in.
        load.assert_not_called()

    def test_loads_and_registers_on_demand(self, mocker: MockerFixture) -> None:
        registry = EmbedderRegistry()
        builtin = _FakeImagePathEmbedder(space_key="mobileclip_s0", dimension=512)
        load = mocker.patch.object(
            embedder_registry, "_load_builtin_embedder", return_value=builtin
        )

        first = registry.get_image_path_embedder()

        assert first is builtin
        load.assert_called_once_with(space_key="mobileclip_s0")

    def test_object_reuse(self, mocker: MockerFixture) -> None:
        registry = EmbedderRegistry()
        builtin = _FakeImagePathEmbedder(space_key="mobileclip_s0", dimension=512)
        load = mocker.patch.object(
            embedder_registry, "_load_builtin_embedder", return_value=builtin
        )

        first = registry.get_image_path_embedder()
        second = registry.get_image_path_embedder()

        assert first is second
        load.assert_called_once()

    def test_reconstruction_by_explicit_key(self, mocker: MockerFixture) -> None:
        registry = EmbedderRegistry()
        builtin = _FakeVideoEmbedder(space_key="PE-Core-T16-384", dimension=512)
        load = mocker.patch.object(
            embedder_registry, "_load_builtin_embedder", return_value=builtin
        )

        embedder = registry.get_video_path_embedder(space_key="PE-Core-T16-384")

        assert embedder is builtin
        load.assert_called_once_with(space_key="PE-Core-T16-384")

    def test_registered_provider_is_authoritative(self, mocker: MockerFixture) -> None:
        registry = EmbedderRegistry()
        registered = _FakeImagePathEmbedder(space_key="mobileclip_s0", dimension=512)
        registry.register(embedder=registered, bootstrap_for=set())
        load = mocker.patch.object(embedder_registry, "_load_builtin_embedder")

        # A registered provider for a built-in key is used without loading the built-in.
        assert registry.get_image_path_embedder(space_key="mobileclip_s0") is registered
        load.assert_not_called()

    def test_partial_registered_provider_used_for_builtin_key(self, mocker: MockerFixture) -> None:
        registry = EmbedderRegistry()
        # A partial provider under the mobileclip key that only embeds text.
        partial = _FakeTextImageEmbedder(space_key="mobileclip_s0", dimension=512)
        registry.register(embedder=partial, bootstrap_for=set())
        load = mocker.patch.object(embedder_registry, "_load_builtin_embedder")

        assert registry.get_text_embedder(space_key="mobileclip_s0") is partial
        load.assert_not_called()

    def test_lazy_loading_preserves_builtin_defaults(self, mocker: MockerFixture) -> None:
        registry = EmbedderRegistry()
        mobileclip = _FakeImagePathEmbedder(space_key="mobileclip_s0", dimension=512)
        perception = _FakeVideoEmbedder(space_key="PE-Core-T16-384", dimension=1024)

        def fake_load(space_key: str) -> Embedder | None:
            return {"mobileclip_s0": mobileclip, "PE-Core-T16-384": perception}.get(space_key)

        mocker.patch.object(embedder_registry, "_load_builtin_embedder", side_effect=fake_load)

        # Loading PE for the video default must not change the image default.
        registry.get_video_path_embedder()

        assert registry.get_bootstrap_space(capability=Capability.IMAGE_PATH) == (
            EmbeddingSpaceSpec(space_key="mobileclip_s0", dimension=512)
        )

    def test_lazy_loading_preserves_custom_defaults(self, mocker: MockerFixture) -> None:
        registry = EmbedderRegistry()
        custom = _FakeImagePathEmbedder(space_key="custom-image", dimension=4)
        registry.register(embedder=custom, bootstrap_for={Capability.IMAGE_PATH})
        perception = _FakeVideoEmbedder(space_key="PE-Core-T16-384", dimension=1024)
        mocker.patch.object(embedder_registry, "_load_builtin_embedder", return_value=perception)

        # Loading a built-in for the video default must not overwrite the custom image default.
        registry.get_video_path_embedder()

        assert registry.get_image_path_embedder() is custom
