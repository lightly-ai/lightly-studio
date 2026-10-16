"""Provider calls that report their usage."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from lightly_studio.assisted_labeling.provider import (
    AssistedLabelingProvider,
    Prediction,
    ProviderImage,
    ProviderNotCalledError,
    SegmentationPrompt,
)
from lightly_studio.usage import usage_reporter

OPERATION_INTERACTIVE = "segment_interactive"
OPERATION_INSTANCES = "segment_instances"


def segment_and_report(  # noqa: PLR0913
    provider: AssistedLabelingProvider,
    image: ProviderImage,
    prompt: SegmentationPrompt,
    operation: str,
    collection_id: uuid.UUID,
    user_email: str | None,
) -> tuple[list[Prediction], float]:
    """Calls the provider, reports the usage, and returns the predictions and latency in ms.

    The usage is reported whether the call succeeds or fails, because the vendor can bill
    a failed call too. A call that fails before it reaches the vendor is not reported.

    Args:
        provider: The provider to call.
        image: The image to segment.
        prompt: The prompts for the image.
        operation: `OPERATION_INTERACTIVE` or `OPERATION_INSTANCES`.
        collection_id: Collection of the image, for the usage report.
        user_email: Email of the user who triggered the call, if known.

    Returns:
        The predictions and the latency of the provider call in milliseconds.

    Raises:
        ProviderError: If the provider fails.
    """
    occurred_at = datetime.now(timezone.utc)
    start = time.perf_counter()
    predictions: list[Prediction] = []
    error: Exception | None = None
    try:
        predictions = provider.segment(image=image, prompt=prompt)
    except ProviderNotCalledError:
        raise
    except Exception as e:
        error = e
    latency_ms = (time.perf_counter() - start) * 1000
    usage_reporter.report(
        events=[
            usage_reporter.UsageEvent(
                event_id=uuid.uuid4(),
                occurred_at=occurred_at,
                user_email=user_email,
                service=usage_reporter.UsageService.AUTOLABELING,
                operation=operation,
                mode=usage_reporter.UsageMode.REALTIME,
                vendor=provider.vendor,
                model=provider.model,
                # The vendor bills per request, failed or not.
                unit=usage_reporter.UsageUnit.REQUEST,
                quantity=1,
                success=error is None,
                collection_id=collection_id,
                latency_ms=latency_ms,
                details={
                    "sample_id": str(image.sample_id),
                    "num_predictions": len(predictions),
                    "provider_id": provider.provider_id,
                },
            )
        ]
    )
    if error is not None:
        raise error
    return predictions, latency_ms
