"""Builds an embedder from the configuration stored on an embedding model.

A remote embedder is registered as data: a URL and a token on the ``embedding_model`` row
of a dataset, written by the GUI or by a script, with no Python object to hand to
``EmbedderRegistry.register``. This module turns such a row into an embedder: the registry
decides which embedder serves a space, and this module owns how one is reached.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

import httpx
from lightly_studio_serve.embedder import Embedder

from lightly_studio.embed.remote import connection
from lightly_studio.embed.remote.embedder import RemoteEmbedder
from lightly_studio.embed.remote.errors import RemoteEmbedderConfigError
from lightly_studio.models.embedding_model import EmbeddingModelTable


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
        config: The stored configuration. It must carry a URL, which the caller checks.

    Returns:
        An embedder that reaches the server and produces the stored space.

    Raises:
        RemoteEmbedderError: If the URL does not parse, the server gives no answer, rejects
            the token, breaks the protocol, advertises no capability that LightlyStudio can
            use, or produces another space than the stored one.
    """
    assert config.url is not None
    try:
        client = connection.build_client(url=config.url)
    except httpx.InvalidURL as error:
        raise RemoteEmbedderConfigError(
            f"The embedding server URL {config.url!r} of space {config.space_key!r} does not parse."
        ) from error
    try:
        embedder = RemoteEmbedder.connect(client=client, api_key=config.api_key)
        _check_identity(embedder=embedder, config=config)
    except Exception:
        client.close()
        raise
    return embedder


def _check_identity(embedder: Embedder, config: EmbedderConfig) -> None:
    """Refuse a server that produces another space than the stored one.

    A mismatch reads like an unreachable server to the caller, which serves the space
    without an embedder instead of failing a request that nobody can answer.

    Raises:
        RemoteEmbedderConfigError: If the space key or the dimension of the server differs
            from the stored one.
    """
    spec = embedder.embedding_space_spec()
    if spec.space_key != config.space_key or spec.dimension != config.dimension:
        raise RemoteEmbedderConfigError(
            f"The embedding server at {config.url} produces {spec.space_key!r} with dimension "
            f"{spec.dimension}. The configuration names {config.space_key!r} with dimension "
            f"{config.dimension}."
        )
