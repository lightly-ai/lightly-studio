"""Handler for getting 2D embeddings from high-dimensional embeddings."""

from __future__ import annotations

from lightly_mundig import TwoDimEmbedding  # type: ignore[import-untyped]

from lightly_studio.dataset.env import LIGHTLY_STUDIO_LICENSE_KEY


# TODO(Malte, 10/2025): Add the get_twodim_embeddings function here that handles the
# caching in the DB and calls _calculate_2d_embeddings when needed.
def _calculate_2d_embeddings(embedding_values: list[list[float]]) -> list[tuple[float, float]]:
    n_samples = len(embedding_values)
    # For 0, 1 or 2 samples we hard-code deterministic coordinates.
    if n_samples == 0:
        return []
    if n_samples == 1:
        return [(0.0, 0.0)]
    if n_samples == 2:  # noqa: PLR2004
        return [(0.0, 0.0), (1.0, 1.0)]

    license_key = LIGHTLY_STUDIO_LICENSE_KEY
    if license_key is None:
        raise ValueError(
            "LIGHTLY_STUDIO_LICENSE_KEY environment variable is not set. "
            "Please set it to your LightlyStudio license key."
        )
    embedding_calculator = TwoDimEmbedding(embedding_values, license_key)
    return embedding_calculator.calculate_2d_embedding()  # type: ignore[no-any-return]
