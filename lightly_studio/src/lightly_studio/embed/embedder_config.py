"""Builds an embedder from the configuration stored on an embedding model.

A remote embedder is registered as data: a URL and a token on the ``embedding_model`` row
of a dataset, written by the GUI or by a script, with no Python object to hand to
``EmbedderRegistry.register``. This module turns such a row into an embedder: the registry
decides which embedder serves a space, and this module owns how one is reached.
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass, field
from uuid import UUID

import httpx
from lightly_studio_serve.embedder import Embedder, ImageBytesEmbedder
from lightly_studio_serve.types import EmbeddingSpaceSpec

from lightly_studio.embed.remote import connection
from lightly_studio.embed.remote.embedder import RemoteEmbedder
from lightly_studio.embed.remote.errors import RemoteEmbedderConfigError
from lightly_studio.models.embedding_model import EmbeddingModelTable

_URL_SCHEMES = frozenset({"http", "https"})


@dataclass(frozen=True)
class EmbedderConfig:
    """The stored configuration of one embedding space, in one dataset.

    The class is frozen, so two configurations compare by value. A caller that caches an
    embedder compares the configuration it built from against the stored one, and builds
    again when they differ.

    Attributes:
        dataset_id: The dataset the configuration belongs to. The same space key in
            another dataset is another row, which can name another backend.
        space_key: The embedding space the built embedder must produce.
        dimension: The dimension the built embedder must produce.
        url: The base URL of the embedding server, or None for a built-in embedder.
        api_key: The bearer token of the server, kept out of a repr.
    """

    dataset_id: UUID
    space_key: str
    dimension: int
    url: str | None = None
    api_key: str | None = field(default=None, repr=False)


@dataclass(frozen=True)
class RemoteDescription:
    """What a remote embedding server advertises.

    Attributes:
        spec: The embedding space that the server produces.
        embeds_images: Whether the server embeds images, which image search needs.
    """

    spec: EmbeddingSpaceSpec
    embeds_images: bool


def from_embedding_model(embedding_model: EmbeddingModelTable) -> EmbedderConfig:
    """Read the configuration of an embedding model row."""
    return EmbedderConfig(
        dataset_id=embedding_model.dataset_id,
        space_key=embedding_model.name,
        dimension=embedding_model.embedding_dimension,
        url=embedding_model.remote_embedder_url,
        api_key=embedding_model.api_key,
    )


def build_remote(config: EmbedderConfig) -> Embedder:
    """Connect to the embedding server that ``config`` names.

    Args:
        config: The stored configuration of a space that a server serves.

    Returns:
        An embedder that reaches the server and produces the stored space.

    Raises:
        RemoteEmbedderError: If the configuration names no server, the URL is not one that
            a request can reach, the URL policy refuses the address, the server gives no
            answer, rejects the token, breaks the protocol, advertises no capability that
            LightlyStudio can use, or produces another space than the stored one.
    """
    if config.url is None:
        raise RemoteEmbedderConfigError(
            f"The configuration of space {config.space_key!r} names no embedding server."
        )
    client = _build_client(url=config.url)
    try:
        embedder = _connect(client=client, url=config.url, api_key=config.api_key)
        check_identity(spec=embedder.embedding_space_spec(), config=config)
    except Exception:
        client.close()
        raise
    return embedder


def describe_remote(url: str, api_key: str | None) -> RemoteDescription:
    """Read what the server at ``url`` advertises.

    Args:
        url: The base URL of the embedding server.
        api_key: The bearer token of the server, or None if the server needs none.

    Returns:
        The embedding space and the capabilities that the server advertises in
        ``/v1/describe``.

    Raises:
        RemoteEmbedderError: For the same causes as ``build_remote``, except a space mismatch.
    """
    client = _build_client(url=url)
    try:
        embedder = _connect(client=client, url=url, api_key=api_key)
        return RemoteDescription(
            spec=embedder.embedding_space_spec(),
            embeds_images=isinstance(embedder, ImageBytesEmbedder),
        )
    finally:
        client.close()


def check_identity(spec: EmbeddingSpaceSpec, config: EmbedderConfig) -> None:
    """Refuse a server that produces another space than the stored one.

    A mismatch reads like an unreachable server to the caller, which serves the space
    without an embedder instead of failing a request that nobody can answer.

    Args:
        spec: The embedding space that the server produces.
        config: The stored configuration that the server must match.

    Raises:
        RemoteEmbedderConfigError: If the space key or the dimension of the server differs
            from the stored one.
    """
    if spec.space_key != config.space_key or spec.dimension != config.dimension:
        raise RemoteEmbedderConfigError(
            f"The embedding server at {config.url!r} produces {spec.space_key!r} with dimension "
            f"{spec.dimension}. The configuration names {config.space_key!r} with dimension "
            f"{config.dimension}."
        )


def _build_client(url: str) -> httpx.Client:
    """Open a client against ``url``.

    Raises:
        RemoteEmbedderConfigError: If the URL does not parse, or is not one that a request
            can reach.
    """
    _check_url(url=url)
    try:
        return connection.build_client(url=url)
    except httpx.InvalidURL as error:
        raise RemoteEmbedderConfigError(
            f"The embedding server URL {url!r} does not parse."
        ) from error


def _connect(client: httpx.Client, url: str, api_key: str | None) -> Embedder:
    """Read ``/v1/describe`` over ``client`` and build the embedder that answers."""
    try:
        return RemoteEmbedder.connect(client=client, api_key=api_key)
    except ValueError as error:
        # `url_policy` refuses an address outside the policy with a `ValueError`, which says
        # nothing to a caller that branches on the errors of this package.
        raise RemoteEmbedderConfigError(
            f"The embedding server URL {url!r} is refused: {error}"
        ) from error


def _check_url(url: str) -> None:
    """Refuse a URL that builds a client but reaches no server.

    Raises:
        RemoteEmbedderConfigError: If the URL does not parse, or carries no http or https
            scheme, or no host.
    """
    # httpx builds a client against a bare host or an unknown scheme without raising, and
    # the failure then arrives from `connect` as an unreachable server, which a caller retries.
    try:
        parsed = urllib.parse.urlsplit(url)
        scheme, host = parsed.scheme, parsed.hostname
    except ValueError:
        # `urlsplit` refuses a malformed bracketed host, such as `http://[::1`.
        scheme, host = "", None
    if scheme not in _URL_SCHEMES or not host:
        raise RemoteEmbedderConfigError(
            f"The embedding server URL {url!r} is not an http or https address with a host."
        )
