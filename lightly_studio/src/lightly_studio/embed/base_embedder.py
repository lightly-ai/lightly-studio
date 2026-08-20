"""Base class embedders inherit and the capability-derivation helper."""

from __future__ import annotations

from lightly_studio.embed.capability import Capability, EmbedderDescriptor
from lightly_studio.embed.protocols import ImagePathEmbedder, TextEmbedder

_CAPABILITY_PROTOCOLS: dict[Capability, type] = {
    Capability.TEXT: TextEmbedder,
    Capability.IMAGE_PATH: ImagePathEmbedder,
}


class BaseEmbedder:
    """Optional convenience base for embedders.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Subclasses implement ``load`` and may use ``_descriptor`` to build its
    result, which fills in the capabilities derived from the capability
    protocols the subclass implements. ``BaseEmbedder`` does not inherit from the
    ``Embedder`` protocol (structural typing already makes any subclass with a
    ``load`` method satisfy ``Embedder``).
    """

    def _descriptor(self, *, model_id: str, dimension: int) -> EmbedderDescriptor:
        """Build a descriptor with capabilities derived from ``self``.

        Args:
            model_id: Stable identity string for the embedder.
            dimension: Length of the embedding vectors the embedder produces.

        Returns:
            The descriptor with model id, dimension, and derived capabilities.
        """
        return EmbedderDescriptor(
            model_id=model_id,
            dimension=dimension,
            capabilities=derive_capabilities(self),
        )


def derive_capabilities(obj: object) -> frozenset[Capability]:
    """Return the capabilities whose protocol ``obj`` implements.

    Args:
        obj: The object to inspect.

    Returns:
        The set of capabilities matching the implemented protocols.
    """
    return frozenset(
        capability
        for capability, protocol in _CAPABILITY_PROTOCOLS.items()
        if isinstance(obj, protocol)
    )
