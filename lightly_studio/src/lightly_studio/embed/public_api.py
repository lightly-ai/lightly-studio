"""Public API for configuring embedders."""

from __future__ import annotations

from collections.abc import Set
from typing import Any
from uuid import UUID

from lightly_studio_serve.embedder import Capability, Embedder
from sqlmodel import Session

from lightly_studio.core.dataset import Dataset
from lightly_studio.embed import embedder_config, embedder_registry
from lightly_studio.embed.embedder_config import EmbedderConfig
from lightly_studio.embed.remote.errors import RemoteEmbedderConfigError
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.resolvers import embedding_model_resolver


def register_default_embedder(
    embedder: Embedder,
    for_capabilities: Set[Capability] | None = None,
) -> None:
    """Register an embedder as the default for the capabilities it implements.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Call this in either of two cases:

    - Before creating a dataset, so that ingestion embeds with ``embedder``. This
      draws on the capabilities for the data being added, such as embedding images,
      image crops, or videos.
    - Before starting the GUI, so that search embeds queries with ``embedder``. This
      draws on the capabilities for the query kinds, such as embedding text, or
      images for reverse-image search. Search resolves the embedder by the collection's
      stored embedding space, so ``embedder`` must share that space to take effect.

    Args:
        embedder: The embedder to register. Its embedding space is read from
            ``embedder.embedding_space_spec()``.
        for_capabilities: Capabilities for which this embedder becomes the default choice.
            By default, all implemented capabilities are updated. An empty set registers
            the embedder without changing the defaults. Requested capabilities the
            embedder does not implement are ignored.

    Raises:
        ValueError: If the embedder implements no capability, or if it shares a space
            with an embedder the registry already holds but does not match its spec.
    """
    embedder_registry.get_registry().register(embedder=embedder, bootstrap_for=for_capabilities)


def register_remote_embedder(dataset: Dataset[Any], url: str, api_key: str | None = None) -> None:
    """Embed search queries of a dataset on a remote embedding server.

    <span class="doc-badge doc-badge--beta">Beta</span>

    The server must produce an embedding space that the dataset already holds embeddings
    in, such as one filled by an embedder registered with ``register_default_embedder``.
    Text and image search in that space then embed the query on the server, starting with
    the next query. An embedder registered in this process for the same space still serves
    the capabilities it implements. A server that embeds no images leaves the space without
    image search. The dataset stores ``url`` and ``api_key`` in plain text.

    See ``examples/example_remote_embedder.py`` for a runnable example.

    Args:
        dataset: The dataset whose embedding space the server produces.
        url: The base URL of a server that ``lightly_studio_serve.serve`` runs, or of
            another server that speaks the same protocol.
        api_key: The bearer token of the server, or None if the server needs none.

    Raises:
        RemoteEmbedderError: If the server cannot be reached or used, or produces an
            embedding space that the dataset does not hold with the same dimension.
            Nothing is stored then.
    """
    spec = embedder_config.describe_remote(url=url, api_key=api_key)
    embedding_model = _get_embedding_model(
        session=dataset.session, dataset_id=dataset.dataset_id, space_key=spec.space_key
    )
    config = EmbedderConfig(
        dataset_id=dataset.dataset_id,
        space_key=embedding_model.name,
        dimension=embedding_model.embedding_dimension,
        url=url,
        api_key=api_key,
    )
    embedder_config.check_identity(spec=spec, config=config)
    embedding_model_resolver.set_remote_embedder(
        session=dataset.session,
        embedding_model_id=embedding_model.embedding_model_id,
        url=url,
        api_key=api_key,
    )


def _get_embedding_model(session: Session, dataset_id: UUID, space_key: str) -> EmbeddingModelTable:
    """Get the embedding model of a space in a dataset.

    Raises:
        RemoteEmbedderConfigError: If the dataset holds no embeddings in the space.
    """
    embedding_models = embedding_model_resolver.get_all_by_dataset_id(
        session=session, dataset_id=dataset_id
    )
    for embedding_model in embedding_models:
        if embedding_model.name == space_key:
            return embedding_model
    known_spaces = [embedding_model.name for embedding_model in embedding_models]
    raise RemoteEmbedderConfigError(
        f"The embedding server produces space {space_key!r}, which the dataset does not hold. "
        f"Known spaces: {known_spaces}."
    )
