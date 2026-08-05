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

    Broken inputs (unreadable/undecodable files) are skipped rather than aborting the
    whole run, so ``embeddings`` may hold fewer rows than the input list. ``kept_indices``
    maps each row back to its position in the input list, in input order, letting callers
    realign any parallel per-input data (e.g. sample IDs) with the embeddings.
    """

    embeddings: NDArray[np.float32]
    """Float32 array of shape ``(len(kept_indices), embedding_dimension)``."""

    kept_indices: list[int]
    """Indices into the input list of the inputs that were embedded, in input order."""
