"""Shared value types for the embedding and labeling paths.

Holds the model-agnostic types passed to and returned by embedders:
``EmbeddingSpaceSpec``, ``EmbeddingResult`` and ``ImageCrop``. It also holds
``PredictedAnnotation``, which a labeling model returns. They live in their own
module so any caller can depend on them without importing the ``Embedder`` or
``LabelingModel`` classes.
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


@dataclass(frozen=True)
class ImageCrop:
    """A rectangular region of an image to embed, given in pixel coordinates.

    <span class="doc-badge doc-badge--beta">Beta</span>
    """

    filepath: str
    """Path to the image the crop is taken from."""

    x: int
    """Left edge of the crop, in pixels from the image's left."""

    y: int
    """Top edge of the crop, in pixels from the image's top."""

    width: int
    """Crop width in pixels."""

    height: int
    """Crop height in pixels."""


@dataclass(frozen=True)
class PredictedAnnotation:
    """An annotation that a labeling model predicted, before the user saves it.

    <span class="doc-badge doc-badge--beta">Beta</span>

    H is the image height and W is the image width, in pixels.
    """

    class_name: str
    """Name of the predicted annotation class."""

    box: tuple[float, float, float, float]
    """Bounding box ``(x_min, y_min, x_max, y_max)`` in pixels."""

    score: float
    """Confidence score, from 0 to 1."""

    mask: NDArray[np.bool_] | None = None
    """Mask of shape ``(H, W)`` and dtype ``np.bool_``, or None for a model without masks."""
