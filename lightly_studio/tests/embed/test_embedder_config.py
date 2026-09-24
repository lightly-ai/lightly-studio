from __future__ import annotations

import uuid

import numpy as np
import pytest
from fastapi.testclient import TestClient
from lightly_studio_serve import server
from lightly_studio_serve.embedder import TextEmbedder
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec
from pytest_mock import MockerFixture

from lightly_studio.embed import embedder_config
from lightly_studio.embed.embedder_config import EmbedderConfig, RemoteDescription
from lightly_studio.embed.remote import connection
from lightly_studio.embed.remote.errors import RemoteEmbedderConfigError
from lightly_studio.models.embedding_model import EmbeddingModelTable

SPACE_KEY = "acme/model@v1"
DIMENSION = 2
URL = "http://embedder.test"


class _ServerEmbedder(TextEmbedder):
    def __init__(self, space_key: str = SPACE_KEY, dimension: int = DIMENSION) -> None:
        self._space_key = space_key
        self._dimension = dimension

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=self._space_key, dimension=self._dimension)

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        return EmbeddingResult(
            embeddings=np.zeros((len(texts), self._dimension), dtype=np.float32),
            kept_indices=list(range(len(texts))),
        )


class TestEmbedderConfig:
    def test_repr__hides_api_key(self) -> None:
        config = _config(api_key="secret-token")

        assert "secret-token" not in repr(config)


def test_from_embedding_model() -> None:
    dataset_id = uuid.uuid4()
    embedding_model = EmbeddingModelTable(
        name=SPACE_KEY,
        embedding_dimension=DIMENSION,
        dataset_id=dataset_id,
        remote_embedder_url=URL,
        api_key="secret-token",
    )

    config = embedder_config.from_embedding_model(embedding_model=embedding_model)

    assert config == EmbedderConfig(
        dataset_id=dataset_id,
        space_key=SPACE_KEY,
        dimension=DIMENSION,
        url=URL,
        api_key="secret-token",
    )


def test_build_remote(mocker: MockerFixture) -> None:
    with _serving(embedder=_ServerEmbedder(), mocker=mocker):
        embedder = embedder_config.build_remote(config=_config())

    assert isinstance(embedder, TextEmbedder)
    assert embedder.embedding_space_spec() == EmbeddingSpaceSpec(
        space_key=SPACE_KEY, dimension=DIMENSION
    )


def test_build_remote__space_key_mismatch(mocker: MockerFixture) -> None:
    serving = _serving(embedder=_ServerEmbedder(space_key="acme/other@v1"), mocker=mocker)

    with serving:
        with pytest.raises(RemoteEmbedderConfigError, match=r"produces 'acme/other@v1'"):
            embedder_config.build_remote(config=_config())

        assert serving.is_closed


def test_build_remote__dimension_mismatch(mocker: MockerFixture) -> None:
    serving = _serving(embedder=_ServerEmbedder(dimension=DIMENSION + 1), mocker=mocker)

    with serving:
        with pytest.raises(RemoteEmbedderConfigError, match=r"dimension 3"):
            embedder_config.build_remote(config=_config())

        assert serving.is_closed


def test_build_remote__no_url() -> None:
    config = EmbedderConfig(
        dataset_id=uuid.uuid4(), space_key=SPACE_KEY, dimension=DIMENSION, url=None
    )

    with pytest.raises(RemoteEmbedderConfigError, match=r"names no embedding server"):
        embedder_config.build_remote(config=config)


def test_build_remote__unparsable_url() -> None:
    config = EmbedderConfig(
        dataset_id=uuid.uuid4(),
        space_key=SPACE_KEY,
        dimension=DIMENSION,
        url="http://embedder.test:notaport",
    )

    with pytest.raises(RemoteEmbedderConfigError, match=r"does not parse"):
        embedder_config.build_remote(config=config)


@pytest.mark.parametrize("url", ["embedder.test", "", "ftp://embedder.test", "http://[::1"])
def test_build_remote__unreachable_url(url: str) -> None:
    config = EmbedderConfig(
        dataset_id=uuid.uuid4(), space_key=SPACE_KEY, dimension=DIMENSION, url=url
    )

    with pytest.raises(RemoteEmbedderConfigError, match=r"is not an http or https address"):
        embedder_config.build_remote(config=config)


def test_describe_remote(mocker: MockerFixture) -> None:
    serving = _serving(embedder=_ServerEmbedder(), mocker=mocker)

    with serving:
        description = embedder_config.describe_remote(url=URL, api_key=None)

        assert serving.is_closed
    assert description == RemoteDescription(
        spec=EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=DIMENSION), embeds_images=False
    )


def test_describe_remote__unreachable_url() -> None:
    with pytest.raises(RemoteEmbedderConfigError, match=r"is not an http or https address"):
        embedder_config.describe_remote(url="embedder.test", api_key=None)


def test_check_identity() -> None:
    embedder_config.check_identity(
        spec=EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=DIMENSION), config=_config()
    )


def test_check_identity__dimension_mismatch() -> None:
    with pytest.raises(RemoteEmbedderConfigError, match=r"dimension 3"):
        embedder_config.check_identity(
            spec=EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=DIMENSION + 1),
            config=_config(),
        )


def _config(api_key: str | None = None) -> EmbedderConfig:
    return EmbedderConfig(
        dataset_id=uuid.uuid4(),
        space_key=SPACE_KEY,
        dimension=DIMENSION,
        url=URL,
        api_key=api_key,
    )


def _serving(embedder: TextEmbedder, mocker: MockerFixture) -> TestClient:
    """Serve ``embedder`` to every client that ``connection.build_client`` opens."""
    client = TestClient(server.create_app(embedder=embedder), follow_redirects=False)
    mocker.patch.object(connection, "build_client", return_value=client)
    return client
