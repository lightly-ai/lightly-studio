"""Base class embedders inherit and the capability-derivation helper."""

from __future__ import annotations

from lightly_studio.embed.capability import Capability, EmbedderDescriptor
from lightly_studio.embed.protocols import ImagePathEmbedder, TextEmbedder

_CAPABILITY_PROTOCOLS: dict[Capability, type] = {
    Capability.TEXT: TextEmbedder,
    Capability.IMAGE_PATH: ImagePathEmbedder,
}


class BaseEmbedder:
    """Base class users inherit to declare a model id and dimension.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Capabilities are derived from the capability protocols the subclass also
    implements. ``BaseEmbedder`` does not inherit from the ``Embedder`` protocol
    (structural typing already makes any subclass satisfy ``Embedder``); it only
    provides ``describe``.
    """

    def __init__(self, *, model_id: str, dimension: int) -> None:
        """Store the embedder's identity and dimension.

        Args:
            model_id: Stable identity string for the embedder.
            dimension: Length of the embedding vectors the embedder produces.
        """
        self._model_id = model_id
        self._dimension = dimension

    def describe(self) -> EmbedderDescriptor:
        """Return the embedder's identity and derived capabilities.

        Returns:
            The descriptor with model id, dimension, and derived capabilities.
        """
        return EmbedderDescriptor(
            model_id=self._model_id,
            dimension=self._dimension,
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
