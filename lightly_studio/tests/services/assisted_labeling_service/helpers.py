"""Helpers for the assisted labeling service tests."""

from __future__ import annotations

from lightly_studio.assisted_labeling.provider import (
    Prediction,
    ProviderImage,
    SegmentationPrompt,
)


class StubProvider:
    """Provider that records the prompts and returns fixed predictions or raises an error."""

    vendor = "stub-vendor"
    model = "stub-model"

    def __init__(
        self, predictions: list[Prediction] | None = None, error: Exception | None = None
    ) -> None:
        self.predictions = predictions or []
        self.error = error
        self.prompts: list[SegmentationPrompt] = []

    def unavailable_reason(self) -> str | None:
        return None

    def segment(self, image: ProviderImage, prompt: SegmentationPrompt) -> list[Prediction]:  # noqa: ARG002
        self.prompts.append(prompt)
        if self.error is not None:
            raise self.error
        return self.predictions
