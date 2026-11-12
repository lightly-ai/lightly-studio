"""Calls of assisted labeling providers."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import TypeVar

from lightly_studio.assisted_labeling.provider import (
    AssistedLabelingProvider,
    Prediction,
    ProviderImage,
    ProviderNotCalledError,
    ProviderUnavailableError,
    SegmentationPrompt,
)
from lightly_studio.errors import NotFoundError
from lightly_studio.usage import usage_reporter

logger = logging.getLogger(__name__)

OPERATION_INTERACTIVE = "segment_interactive"
OPERATION_INSTANCES = "segment_instances"

_PredictionT = TypeVar("_PredictionT")


def segment(  # noqa: PLR0913
    provider: AssistedLabelingProvider,
    image: ProviderImage,
    prompt: SegmentationPrompt,
    operation: str,
    collection_id: uuid.UUID,
    user_email: str | None,
) -> list[Prediction]:
    """Returns the predictions of the provider for the image and the prompt.

    Reports the usage whether the call succeeds or fails, because the vendor can bill a
    failed call too. A call that fails before it reaches the vendor is not reported.

    Args:
        provider: The provider to call.
        image: The image to segment.
        prompt: The prompts for the image.
        operation: `OPERATION_INTERACTIVE` or `OPERATION_INSTANCES`.
        collection_id: Collection of the image, for the usage report.
        user_email: Email of the user who triggered the call, if known.

    Raises:
        ProviderUnavailableError: If the provider is not configured.
        NotFoundError: If the image file cannot be read.
        ProviderError: If the provider fails.
    """
    return _call_and_report(
        call=lambda: provider.segment(image=image, prompt=prompt),
        vendor=provider.vendor,
        model=provider.model,
        operation=operation,
        sample_id=image.sample_id,
        collection_id=collection_id,
        user_email=user_email,
    )


# PLR0913: Every argument is a field of the usage event.
def _call_and_report(  # noqa: PLR0913
    call: Callable[[], list[_PredictionT]],
    vendor: str,
    model: str,
    operation: str,
    sample_id: uuid.UUID,
    collection_id: uuid.UUID,
    user_email: str | None,
) -> list[_PredictionT]:
    """Run `call`, report its usage, and return its predictions.

    Reports the usage whether the call succeeds or fails. A call that fails before it
    reaches the vendor is not reported.
    """
    occurred_at = datetime.now(timezone.utc)
    start = time.perf_counter()
    predictions: list[_PredictionT] = []
    error: Exception | None = None
    try:
        predictions = call()
    except (ProviderNotCalledError, ProviderUnavailableError, NotFoundError):
        # The vendor was not called, for example because the image file cannot be read
        raise
    except Exception as e:
        error = e
    latency_ms = (time.perf_counter() - start) * 1000
    logger.debug("Ran %s on sample %s in %.0f ms.", operation, sample_id, latency_ms)
    usage_reporter.report(
        events=[
            usage_reporter.UsageEvent(
                event_id=uuid.uuid4(),
                occurred_at=occurred_at,
                user_email=user_email,
                service=usage_reporter.UsageService.AUTOLABELING,
                operation=operation,
                mode=usage_reporter.UsageMode.REALTIME,
                vendor=vendor,
                model=model,
                # The vendor bills per request, failed or not
                unit=usage_reporter.UsageUnit.REQUEST,
                quantity=1,
                success=error is None,
                collection_id=collection_id,
                latency_ms=latency_ms,
                details={
                    "sample_id": str(sample_id),
                    "num_predictions": len(predictions),
                },
            )
        ]
    )
    if error is not None:
        raise error
    return predictions
