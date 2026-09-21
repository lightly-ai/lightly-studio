from __future__ import annotations

import logging
import uuid
from uuid import UUID

import numpy as np
import pytest
from lightly_studio_serve.embedder import (
    Capability,
    Embedder,
    ImagePathEmbedder,
    TextEmbedder,
    VideoPathEmbedder,
)
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec
from pytest_mock import MockerFixture

from lightly_studio.embed import embedder_config, embedder_registry
from lightly_studio.embed.embedder_config import EmbedderConfig
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.random_embedder import RandomEmbedder
from lightly_studio.embed.remote.errors import RemoteEmbedderUnreachableError


class _FakeTextImageEmbedder(TextEmbedder, ImagePathEmbedder):
    def __init__(self, space_key: str, dimension: int = 2) -> None:
        self._space_key = space_key
        self._dimension = dimension

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=self._space_key, dimension=self._dimension)

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        return EmbeddingResult(
            embeddings=np.zeros((len(texts), self._dimension), dtype=np.float32),
            kept_indices=list(range(len(texts))),
        )

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        return EmbeddingResult(
            embeddings=np.zeros((len(paths), self._dimension), dtype=np.float32),
            kept_indices=list(range(len(paths))),
        )


class _FakeNoCapabilityEmbedder(Embedder):
    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key="none", dimension=2)


class _FakeImageEmbedder(ImagePathEmbedder):
    def __init__(self, space_key: str, dimension: int = 2) -> None:
        self._space_key = space_key
        self._dimension = dimension

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=self._space_key, dimension=self._dimension)

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        return EmbeddingResult(
            embeddings=np.zeros((len(paths), self._dimension), dtype=np.float32),
            kept_indices=list(range(len(paths))),
        )


class _FakeVideoImageEmbedder(VideoPathEmbedder, ImagePathEmbedder):
    def __init__(self, space_key: str) -> None:
        self._space_key = space_key

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=self._space_key, dimension=2)

    def embed_videos(self, paths: list[str]) -> EmbeddingResult:
        return EmbeddingResult(
            embeddings=np.zeros((len(paths), 2), dtype=np.float32),
            kept_indices=list(range(len(paths))),
        )

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        return self.embed_videos(paths=paths)


class TestEmbedderRegistry:
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

    def test_register__replacement_does_not_compose_capabilities(self) -> None:
        registry = EmbedderRegistry()
        registry.register(embedder=_FakeTextImageEmbedder(space_key="space-a"))
        replacement = _FakeImageEmbedder(space_key="space-a")

        registry.register(embedder=replacement, bootstrap_for=set())

        assert registry.get_image_path_embedder() is replacement
        assert registry.get_text_embedder() is None

    def test_register__conflicting_spec_raises(self) -> None:
        registry = EmbedderRegistry()
        registered = _FakeTextImageEmbedder(space_key="space-a", dimension=2)
        registry.register(embedder=registered)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(embedder=_FakeTextImageEmbedder(space_key="space-a", dimension=3))

        assert registry.get_text_embedder(space_key="space-a") is registered

    def test_register__separate_spaces(self) -> None:
        registry = EmbedderRegistry()
        embedder_a = _FakeTextImageEmbedder(space_key="space-a")
        embedder_b = _FakeTextImageEmbedder(space_key="space-b")

        registry.register(embedder=embedder_a)
        registry.register(embedder=embedder_b)

        assert registry.get_text_embedder(space_key="space-a") is embedder_a
        assert registry.get_text_embedder(space_key="space-b") is embedder_b

    def test_register__sets_all_implemented_bootstrap_spaces_by_default(self) -> None:
        registry = EmbedderRegistry()
        embedder = RandomEmbedder()

        registry.register(embedder=embedder)

        assert registry.get_image_path_embedder() is embedder
        assert registry.get_text_embedder() is embedder
        assert registry.get_image_bytes_embedder() is embedder

    def test_register__empty_bootstrap_set_preserves_defaults(self, mocker: MockerFixture) -> None:
        registry = EmbedderRegistry()
        embedder = _FakeTextImageEmbedder(space_key="space-a")
        load_builtin = mocker.patch.object(
            embedder_registry, "_load_builtin_embedder", return_value=None
        )

        registry.register(embedder=embedder, bootstrap_for=set())

        assert registry.get_image_path_embedder() is None
        assert registry.get_text_embedder() is None
        load_builtin.assert_called_once_with(space_key="mobileclip_s0")

    def test_register__explicit_bootstrap_set_uses_supported_intersection(
        self, mocker: MockerFixture
    ) -> None:
        registry = EmbedderRegistry()
        embedder = _FakeTextImageEmbedder(space_key="space-a")
        video = _FakeVideoImageEmbedder(space_key="PE-Core-T16-384")
        mocker.patch.object(embedder_registry, "_load_builtin_embedder", return_value=video)

        registry.register(
            embedder=embedder,
            bootstrap_for={Capability.IMAGE_PATH, Capability.VIDEO_PATH},
        )

        assert registry.get_image_path_embedder() is embedder
        assert registry.get_text_embedder() is None
        assert registry.get_video_path_embedder() is video

    def test_register__instances_have_independent_bootstrap_spaces(
        self, mocker: MockerFixture
    ) -> None:
        first = EmbedderRegistry()
        second = EmbedderRegistry()
        custom = _FakeImageEmbedder(space_key="custom")
        builtin = _FakeImageEmbedder(space_key="mobileclip_s0")
        mocker.patch.object(embedder_registry, "_load_builtin_embedder", return_value=builtin)

        first.register(embedder=custom)

        assert first.get_image_path_embedder() is custom
        assert second.get_image_path_embedder() is builtin

    def test_get_text_embedder__missing(self) -> None:
        registry = EmbedderRegistry()

        assert registry.get_text_embedder(space_key="space-a") is None
        assert registry.get_text_embedder() is None

    def test_get_text_embedder__from_config(self, mocker: MockerFixture) -> None:
        registry = EmbedderRegistry()
        remote = _FakeTextImageEmbedder(space_key="space-a")
        build_remote = mocker.patch.object(embedder_config, "build_remote", return_value=remote)
        config = _config(space_key="space-a", url="http://first.test")

        assert registry.get_text_embedder(space_key="space-a", config=config) is remote
        # The embedder is cached, so a second query does not build it again.
        assert registry.get_text_embedder(space_key="space-a", config=config) is remote
        build_remote.assert_called_once_with(config=config)

    def test_get_text_embedder__registered_embedder_wins_over_config(
        self, mocker: MockerFixture
    ) -> None:
        registry = EmbedderRegistry()
        registered = _FakeTextImageEmbedder(space_key="space-a")
        registry.register(embedder=registered)
        build_remote = mocker.patch.object(embedder_config, "build_remote")

        embedder = registry.get_text_embedder(
            space_key="space-a", config=_config(space_key="space-a", url="http://first.test")
        )

        assert embedder is registered
        build_remote.assert_not_called()

    def test_get_text_embedder__config_wins_over_loaded_builtin(
        self, mocker: MockerFixture
    ) -> None:
        registry = EmbedderRegistry()
        builtin = _FakeTextImageEmbedder(space_key="mobileclip_s0")
        remote = _FakeTextImageEmbedder(space_key="mobileclip_s0")
        mocker.patch.object(embedder_registry, "_load_builtin_embedder", return_value=builtin)
        mocker.patch.object(embedder_config, "build_remote", return_value=remote)

        # A dataset without a configuration loads the builtin of the space first.
        assert registry.get_text_embedder(space_key="mobileclip_s0") is builtin
        embedder = registry.get_text_embedder(
            config=_config(space_key="mobileclip_s0", url="http://first.test")
        )

        assert embedder is remote
        # The builtin still serves the dataset that configures no server.
        assert registry.get_text_embedder(space_key="mobileclip_s0") is builtin

    def test_get_text_embedder__config_does_not_register_its_space(
        self, mocker: MockerFixture
    ) -> None:
        registry = EmbedderRegistry()
        builtin = _FakeTextImageEmbedder(space_key="mobileclip_s0")
        remote = _FakeTextImageEmbedder(space_key="mobileclip_s0")
        mocker.patch.object(embedder_registry, "_load_builtin_embedder", return_value=builtin)
        mocker.patch.object(embedder_config, "build_remote", return_value=remote)

        # The reverse order: the configured dataset resolves before the builtin loads.
        assert (
            registry.get_text_embedder(
                config=_config(space_key="mobileclip_s0", url="http://first.test")
            )
            is remote
        )

        assert registry.get_text_embedder(space_key="mobileclip_s0") is builtin

    def test_get_text_embedder__changed_url_rebuilds(self, mocker: MockerFixture) -> None:
        registry = EmbedderRegistry()
        first = _FakeTextImageEmbedder(space_key="space-a")
        second = _FakeTextImageEmbedder(space_key="space-a")
        mocker.patch.object(embedder_config, "build_remote", side_effect=[first, second])
        dataset_id = uuid.uuid4()

        embedder = registry.get_text_embedder(
            config=_config(space_key="space-a", url="http://first.test", dataset_id=dataset_id)
        )
        rebuilt = registry.get_text_embedder(
            config=_config(space_key="space-a", url="http://second.test", dataset_id=dataset_id)
        )

        assert embedder is first
        assert rebuilt is second

    def test_get_text_embedder__config_of_two_datasets(self, mocker: MockerFixture) -> None:
        registry = EmbedderRegistry()
        first = _FakeTextImageEmbedder(space_key="space-a")
        second = _FakeTextImageEmbedder(space_key="space-a")
        mocker.patch.object(embedder_config, "build_remote", side_effect=[first, second])

        # The same space key in two datasets can name two backends.
        embedder_of_first = registry.get_text_embedder(
            config=_config(space_key="space-a", url="http://first.test")
        )
        embedder_of_second = registry.get_text_embedder(
            config=_config(space_key="space-a", url="http://second.test")
        )

        assert embedder_of_first is first
        assert embedder_of_second is second

    def test_get_text_embedder__unusable_server(
        self, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
    ) -> None:
        registry = EmbedderRegistry()
        mocker.patch.object(
            embedder_config, "build_remote", side_effect=RemoteEmbedderUnreachableError("down")
        )

        with caplog.at_level(logging.WARNING):
            embedder = registry.get_text_embedder(
                config=_config(space_key="space-a", url="http://first.test")
            )

        assert embedder is None
        assert "Cannot use the embedding server" in caplog.text

    def test_get_text_embedder__config_without_url_loads_builtin(
        self, mocker: MockerFixture
    ) -> None:
        registry = EmbedderRegistry()
        builtin = _FakeTextImageEmbedder(space_key="mobileclip_s0")
        mocker.patch.object(embedder_registry, "_load_builtin_embedder", return_value=builtin)
        build_remote = mocker.patch.object(embedder_config, "build_remote")

        embedder = registry.get_text_embedder(config=_config(space_key="mobileclip_s0"))

        assert embedder is builtin
        build_remote.assert_not_called()

    def test_get_text_embedder__unusable_server_is_not_retried(self, mocker: MockerFixture) -> None:
        registry = EmbedderRegistry()
        build_remote = mocker.patch.object(
            embedder_config, "build_remote", side_effect=RemoteEmbedderUnreachableError("down")
        )
        config = _config(space_key="space-a", url="http://first.test")

        assert registry.get_text_embedder(config=config) is None
        assert registry.get_text_embedder(config=config) is None

        build_remote.assert_called_once_with(config=config)

    def test_get_text_embedder__changed_config_retries_after_failure(
        self, mocker: MockerFixture
    ) -> None:
        registry = EmbedderRegistry()
        remote = _FakeTextImageEmbedder(space_key="space-a")
        mocker.patch.object(
            embedder_config,
            "build_remote",
            side_effect=[RemoteEmbedderUnreachableError("down"), remote],
        )
        dataset_id = uuid.uuid4()

        first = registry.get_text_embedder(
            config=_config(space_key="space-a", url="http://first.test", dataset_id=dataset_id)
        )
        second = registry.get_text_embedder(
            config=_config(space_key="space-a", url="http://second.test", dataset_id=dataset_id)
        )

        assert first is None
        assert second is remote

    def test_get_image_path_embedder__explicit_key_has_no_fallback(
        self, mocker: MockerFixture
    ) -> None:
        registry = EmbedderRegistry()
        default = _FakeImageEmbedder(space_key="default")
        registry.register(embedder=default)
        load_builtin = mocker.patch.object(
            embedder_registry, "_load_builtin_embedder", return_value=None
        )

        assert registry.get_image_path_embedder(space_key="unknown") is None
        load_builtin.assert_called_once_with(space_key="unknown")

    def test_get_image_crop_path_embedder__registered_partial_builtin_is_authoritative(
        self, mocker: MockerFixture
    ) -> None:
        registry = EmbedderRegistry()
        partial = _FakeImageEmbedder(space_key="mobileclip_s0")
        registry.register(embedder=partial, bootstrap_for=set())
        load_builtin = mocker.patch.object(embedder_registry, "_load_builtin_embedder")

        assert registry.get_image_crop_path_embedder() is None
        load_builtin.assert_not_called()

    def test_get_video_path_embedder__loads_builtin_once(self, mocker: MockerFixture) -> None:
        registry = EmbedderRegistry()
        pe = _FakeVideoImageEmbedder(space_key="PE-Core-T16-384")
        mobileclip = _FakeImageEmbedder(space_key="mobileclip_s0")
        load_builtin = mocker.patch.object(
            embedder_registry, "_load_builtin_embedder", side_effect=[pe, mobileclip]
        )

        assert registry.get_video_path_embedder() is pe
        assert registry.get_image_path_embedder(space_key="PE-Core-T16-384") is pe
        assert registry.get_image_path_embedder() is mobileclip
        assert load_builtin.call_count == 2
        load_builtin.assert_any_call(space_key="PE-Core-T16-384")
        load_builtin.assert_any_call(space_key="mobileclip_s0")

    def test_lazy_loading_preserves_custom_bootstrap_space(self, mocker: MockerFixture) -> None:
        registry = EmbedderRegistry()
        custom = _FakeImageEmbedder(space_key="custom")
        builtin = _FakeTextImageEmbedder(space_key="mobileclip_s0")
        registry.register(embedder=custom)
        mocker.patch.object(embedder_registry, "_load_builtin_embedder", return_value=builtin)

        assert registry.get_image_path_embedder(space_key="mobileclip_s0") is builtin
        assert registry.get_image_path_embedder() is custom

    def test_preload_builtin_embedders__loads_each_builtin_once(
        self, mocker: MockerFixture
    ) -> None:
        registry = EmbedderRegistry()
        mobileclip = _FakeTextImageEmbedder(space_key="mobileclip_s0")
        pe = _FakeVideoImageEmbedder(space_key="PE-Core-T16-384")
        builtins = {"mobileclip_s0": mobileclip, "PE-Core-T16-384": pe}
        load_builtin = mocker.patch.object(
            embedder_registry,
            "_load_builtin_embedder",
            side_effect=lambda space_key: builtins[space_key],
        )

        registry.preload_builtin_embedders()

        # The bootstrap capabilities share two spaces, so each builtin loads exactly once.
        assert load_builtin.call_count == 2
        load_builtin.assert_any_call(space_key="mobileclip_s0")
        load_builtin.assert_any_call(space_key="PE-Core-T16-384")
        assert registry.get_image_path_embedder() is mobileclip
        assert registry.get_video_path_embedder() is pe

    def test_preload_builtin_embedders__reuses_registered_embedder(
        self, mocker: MockerFixture
    ) -> None:
        registry = EmbedderRegistry()
        custom = _FakeVideoImageEmbedder(space_key="PE-Core-T16-384")
        registry.register(embedder=custom, bootstrap_for={Capability.VIDEO_PATH})
        mobileclip = _FakeTextImageEmbedder(space_key="mobileclip_s0")
        load_builtin = mocker.patch.object(
            embedder_registry, "_load_builtin_embedder", return_value=mobileclip
        )

        registry.preload_builtin_embedders()

        # The registered custom embedder covers its space, so only the image builtin loads.
        load_builtin.assert_called_once_with(space_key="mobileclip_s0")
        assert registry.get_video_path_embedder() is custom


def _config(
    space_key: str,
    url: str | None = None,
    dataset_id: UUID | None = None,
) -> EmbedderConfig:
    return EmbedderConfig(
        dataset_id=dataset_id or uuid.uuid4(),
        space_key=space_key,
        dimension=2,
        url=url,
    )


def test_get_registry__returns_process_wide_instance() -> None:
    assert embedder_registry.get_registry() is embedder_registry.get_registry()
