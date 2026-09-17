"""Public API for configuring embedders."""

from __future__ import annotations

from collections.abc import Set

from lightly_studio_serve.embedder import Capability, Embedder

from lightly_studio.embed import embedder_registry


def register_default_embedder(
    embedder: Embedder,
    for_capabilities: Set[Capability] | None = None,
) -> None:
    """Register an embedder as the default for the capabilities it implements.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Call this before creating a dataset so that ingestion uses ``embedder`` instead
    of the built-in default. A thin wrapper over the process-wide embedder registry.

    Args:
        embedder: The embedder to register. Its embedding space is read from
            ``embedder.embedding_space_spec()``.
        for_capabilities: Capabilities for which this embedder becomes the default choice.
            By default, all implemented capabilities are updated. An empty set registers
            the embedder without changing the defaults. Requested capabilities the
            embedder does not implement are ignored.

    Raises:
        ValueError: If the embedder implements no capability, or if it shares a space
            with an already registered embedder but does not match its spec.
    """
    embedder_registry.get_registry().register(embedder=embedder, bootstrap_for=for_capabilities)
