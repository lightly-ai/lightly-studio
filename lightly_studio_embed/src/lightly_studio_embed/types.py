"""Value types every embedder passes and returns, LightlyStudio's own included.

``EmbeddingSpaceSpec`` names the embedding space a model produces and
``EmbeddingResult`` carries the vectors it produced. They live in their own module
so a caller can depend on them without importing the embedder classes.

``lightly-studio`` imports both from here rather than declaring its own, so the
two packages cannot drift apart. That is also why this package depends on numpy:
LightlyStudio's ingest paths index and slice ``embeddings`` as an array, and a
plain nested sequence cannot carry that.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class EmbeddingSpaceSpec:
    """Identity and shape of the embedding space an embedder produces.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Stored in the database so the same embedding space can be recognized across
    LightlyStudio runs.
    """

    space_key: str
    """Stable identifier for the embedding space.

    Two embedders that share a ``space_key`` are treated as producing the same
    embedding space, so their vectors are comparable. Change it whenever the
    produced vectors become incomparable, e.g. for a model version change. Can be
    any string, e.g. ``your-company/model-family@version``.
    """

    dimension: int
    """Length of each embedding vector this embedder produces."""


@dataclass(frozen=True)
class EmbeddingResult:
    """Embeddings for the inputs that could be read, plus which inputs they cover.

    <span class="doc-badge doc-badge--beta">Beta</span>

    An embedder skips broken inputs (files it cannot read or decode) instead of
    failing the whole batch, so ``embeddings`` can have fewer rows than the input
    list. ``kept_indices`` gives the position of each row in the input list, in
    input order. Use it to line up the embeddings with any per-input data you keep
    on the side, such as sample IDs.
    """

    embeddings: NDArray[np.float32]
    """Float32 array of shape ``(len(kept_indices), embedding_dimension)``."""

    kept_indices: list[int]
    """Indices into the input list of the inputs that were embedded, in input order."""
