"""Calls of assisted labeling providers."""

from __future__ import annotations

import logging
import time

from lightly_studio.assisted_labeling.provider import (
    AssistedLabelingProvider,
    Prediction,
    ProviderImage,
    SegmentationPrompt,
)

logger = logging.getLogger(__name__)


def segment(
    provider: AssistedLabelingProvider, image: ProviderImage, prompt: SegmentationPrompt
) -> list[Prediction]:
    """Returns the predictions of the provider for the image and the prompt.

    Raises:
        ProviderError: If the provider fails.
    """
    start = time.perf_counter()
    predictions = provider.segment(image=image, prompt=prompt)
    logger.debug(
        "Provider '%s' segmented sample %s in %.0f ms.",
        provider.provider_id,
        image.sample_id,
        (time.perf_counter() - start) * 1000,
    )
    return predictions
