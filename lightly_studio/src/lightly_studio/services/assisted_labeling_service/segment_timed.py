"""Timed segmentation calls."""

from __future__ import annotations

import time

from lightly_studio.assisted_labeling.provider import (
    AssistedLabelingProvider,
    Prediction,
    ProviderImage,
    SegmentationPrompt,
)


def segment_timed(
    provider: AssistedLabelingProvider, image: ProviderImage, prompt: SegmentationPrompt
) -> tuple[list[Prediction], float]:
    """Calls the provider and returns its predictions and the latency in milliseconds.

    Raises:
        ProviderError: If the provider fails.
    """
    start = time.perf_counter()
    predictions = provider.segment(image=image, prompt=prompt)
    latency_ms = (time.perf_counter() - start) * 1000
    return predictions, latency_ms
