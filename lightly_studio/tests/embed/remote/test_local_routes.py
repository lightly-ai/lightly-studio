from __future__ import annotations

from collections.abc import Iterator

import pytest
from lightly_studio_serve.embedder import ImageBytesEmbedder, ImagePathEmbedder
from lightly_studio_serve.protocol import ServerLimits
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec

from lightly_studio.embed.remote import connection, local_routes
from lightly_studio.embed.remote.embedder import RemoteEmbedder
from lightly_studio.embed.remote.transport import RemoteTransport
from tests.embed.remote import threaded_server
from tests.embed.remote.helpers import DIMENSION, SPACE_KEY, FakeImageEmbedder, FakeServer

LIMITS = ServerLimits(max_batch_size=2, max_request_bytes=1024)


class CustomRemoteEmbedder(RemoteEmbedder, ImageBytesEmbedder):
    """A remote embedder that a caller writes by hand, and not ``connect``."""

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        raise NotImplementedError


@pytest.fixture(scope="module")
def remote() -> Iterator[RemoteEmbedder]:
    """A server that embeds image bytes, and one client for the tests of this module."""
    with (
        threaded_server.serve(embedder=FakeImageEmbedder(), limits=LIMITS) as url,
        connection.build_client(url=url) as client,
    ):
        yield RemoteEmbedder.connect(client=client)


def test_with_local_routes(remote: RemoteEmbedder) -> None:
    embedder = local_routes.with_local_routes(embedder=remote)

    assert isinstance(embedder, ImagePathEmbedder)
    assert isinstance(embedder, ImageBytesEmbedder)
    assert embedder.embedding_space_spec() == remote.embedding_space_spec()
    assert isinstance(embedder, RemoteEmbedder)
    assert embedder.remote_endpoint() is not None
    assert embedder.remote_endpoint() == remote.remote_endpoint()


def test_with_local_routes__local_embedder() -> None:
    embedder = FakeImageEmbedder()

    assert local_routes.with_local_routes(embedder=embedder) is embedder


def test_with_local_routes__remote_without_image_bytes() -> None:
    with FakeServer(capabilities=["text"]).client() as client:
        embedder = RemoteEmbedder.connect(client=client)

    assert local_routes.with_local_routes(embedder=embedder) is embedder


def test_with_local_routes__custom_remote_subclass() -> None:
    with FakeServer(capabilities=["image_bytes"]).client() as client:
        embedder = CustomRemoteEmbedder(
            transport=RemoteTransport(client=client),
            spec=EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=DIMENSION),
            limits=LIMITS,
        )

    assert local_routes.with_local_routes(embedder=embedder) is embedder
