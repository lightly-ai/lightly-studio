"""Calls of assisted labeling providers."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone

from lightly_studio.assisted_labeling.labeling_model import (
    LabelingImage,
    LabelingModel,
    PredictedAnnotation,
)
from lightly_studio.assisted_labeling.provider import (
    AssistedLabelingProvider,
    Prediction,
    ProviderNotCalledError,
    ProviderUnavailableError,
    SegmentationPrompt,
)
from lightly_studio.errors import NotFoundError
from lightly_studio.usage import usage_reporter

logger = logging.getLogger(__name__)

OPERATION_INTERACTIVE = "segment_interactive"
OPERATION_INSTANCES = "segment_instances"
OPERATION_MODEL = "label_with_model"


def segment(  # noqa: PLR0913
    provider: AssistedLabelingProvider,
    image: LabelingImage,
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
    occurred_at = datetime.now(timezone.utc)
    start = time.perf_counter()
    predictions: list[Prediction] = []
    error: Exception | None = None
    try:
        predictions = provider.segment(image=image, prompt=prompt)
    except (ProviderNotCalledError, ProviderUnavailableError, NotFoundError):
        # The vendor was not called, for example because the image file cannot be read
        raise
    except Exception as e:
        error = e
    latency_ms = (time.perf_counter() - start) * 1000
    logger.debug("Segmented sample %s in %.0f ms.", image.sample_id, latency_ms)
    _report_usage(
        vendor=provider.vendor,
        model=provider.model,
        operation=operation,
        occurred_at=occurred_at,
        latency_ms=latency_ms,
        success=error is None,
        collection_id=collection_id,
        user_email=user_email,
        details={"sample_id": str(image.sample_id), "num_predictions": len(predictions)},
    )
    if error is not None:
        raise error
    return predictions


def predict(
    model: LabelingModel,
    image: LabelingImage,
    threshold: float,
    collection_id: uuid.UUID,
    user_email: str | None,
) -> list[PredictedAnnotation]:
    """Returns the predictions of the model for the image.

    Reports the usage like `segment`.

    Args:
        model: The model to run.
        image: The image to label.
        threshold: Minimum confidence score that the user selected.
        collection_id: Collection of the image, for the usage report.
        user_email: Email of the user who triggered the call, if known.

    Raises:
        ProviderUnavailableError: If the model is not configured.
        NotFoundError: If the image file cannot be read.
        ProviderError: If the model fails.
        Exception: Any other error of the model.
    """
    occurred_at = datetime.now(timezone.utc)
    start = time.perf_counter()
    predictions: list[PredictedAnnotation] = []
    error: Exception | None = None
    try:
        predictions = model.predict(image=image, threshold=threshold)
    except (ProviderNotCalledError, ProviderUnavailableError, NotFoundError):
        raise
    except Exception as e:
        error = e
    latency_ms = (time.perf_counter() - start) * 1000
    logger.debug("Ran %s on sample %s in %.0f ms.", model.model_id, image.sample_id, latency_ms)
    _report_usage(
        vendor=model.vendor,
        model=model.model_id,
        operation=OPERATION_MODEL,
        occurred_at=occurred_at,
        latency_ms=latency_ms,
        success=error is None,
        collection_id=collection_id,
        user_email=user_email,
        details={"sample_id": str(image.sample_id), "num_predictions": len(predictions)},
    )
    if error is not None:
        raise error
    return predictions


def _report_usage(  # noqa: PLR0913
    vendor: str,
    model: str,
    operation: str,
    occurred_at: datetime,
    latency_ms: float,
    success: bool,
    collection_id: uuid.UUID,
    user_email: str | None,
    details: dict[str, object],
) -> None:
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
                success=success,
                collection_id=collection_id,
                latency_ms=latency_ms,
                details=details,
            )
        ]
    )
