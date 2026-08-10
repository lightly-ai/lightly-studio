"""Result type shared by the batched embedding paths.

Holds ``EmbeddingResult``, the model-agnostic return type used across the
image, image-crop, and video embedding paths. It lives in its own module so any
embedding path can depend on it without pulling in a path-specific module.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class EmbeddingResult:
    """Embeddings for the inputs that could be read, plus which inputs they cover.

    <span class="doc-badge doc-badge--beta">Beta</span>

    A generator skips broken inputs (files it cannot read or decode) instead of failing
    the whole run, so ``embeddings`` can have fewer rows than the input list.
    ``kept_indices`` gives the position of each row in the input list, in input order.
    Use it to line up the embeddings with any per-input data you keep on the side, such
    as sample IDs.
    """

    embeddings: NDArray[np.float32]
    """Float32 array of shape ``(len(kept_indices), embedding_dimension)``."""

    kept_indices: list[int]
    """Indices into the input list of the inputs that were embedded, in input order."""
