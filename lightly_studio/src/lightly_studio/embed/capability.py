"""Capabilities an embedder can offer and the descriptor that reports them."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Capability(str, Enum):
    """A kind of input an embedder can turn into a vector.

    <span class="doc-badge doc-badge--beta">Beta</span>
    """

    TEXT = "text"
    IMAGE_PATH = "image_path"
    # More capabilities (image_bytes, crop_path, crop_bytes, frame, video_path)
    # will be added with the remote/online work. Kept minimal for the prototype.


@dataclass(frozen=True)
class EmbedderDescriptor:
    """Identity and capabilities of an embedder.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Attributes:
        model_id: Stable identity string for the embedder. Reused as both the DB row
            name and hash.
        dimension: Length of the embedding vectors the embedder produces.
        capabilities: The capabilities derived from the protocols the embedder
            implements. Runtime-only, not persisted.
    """

    model_id: str
    dimension: int
    capabilities: frozenset[Capability]
