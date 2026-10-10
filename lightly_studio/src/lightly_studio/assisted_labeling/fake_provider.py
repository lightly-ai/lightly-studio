"""Deterministic offline provider for tests and demos."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from lightly_studio.assisted_labeling.provider import (
    BoxPrompt,
    PointPrompt,
    Prediction,
    ProviderCapabilities,
    ProviderImage,
    SegmentationPrompt,
)

FAKE_SCORE = 0.9
MAX_TEXT_BLOBS = 3


class FakeProvider:
    """Returns simple geometric masks without a model or network access.

    - Text prompt: up to 3 disks in a row, with the text as class name.
    - Box prompts: an ellipse inside each box, or the union of the ellipses if
      `max_masks` is 1.
    - Point prompts: a disk around the centroid of the positive points, without the
      pixels near negative points.
    """

    provider_id = "fake"
    display_name = "Fake (offline)"
    sends_data_to_third_party = False

    def capabilities(self) -> ProviderCapabilities:
        """Returns support for all prompt types."""
        return ProviderCapabilities(
            positive_points=True,
            negative_points=True,
            boxes=True,
            text_prompt=True,
            max_instances=MAX_TEXT_BLOBS,
        )

    def is_available(self) -> str | None:
        """Returns None, the fake provider is always usable."""
        return None

    def prepare(self, image: ProviderImage) -> None:
        """Does nothing."""

    def segment(self, image: ProviderImage, prompt: SegmentationPrompt) -> list[Prediction]:
        """Returns deterministic masks for the prompt. See the class docstring."""
        if prompt.text:
            return _segment_text(
                width=image.width, height=image.height, text=prompt.text, max_masks=prompt.max_masks
            )
        if prompt.boxes:
            return _segment_boxes(
                width=image.width,
                height=image.height,
                boxes=prompt.boxes,
                max_masks=prompt.max_masks,
            )
        return _segment_points(width=image.width, height=image.height, points=prompt.points)


def _segment_text(width: int, height: int, text: str, max_masks: int) -> list[Prediction]:
    count = min(max_masks, MAX_TEXT_BLOBS)
    radius = _radius(width=width, height=height)
    return [
        Prediction(
            mask=_ellipse_mask(
                shape=(height, width),
                center=(width * (index + 1) / (MAX_TEXT_BLOBS + 1), height / 2),
                radii=(radius, radius),
            ),
            score=FAKE_SCORE,
            class_name=text,
        )
        for index in range(count)
    ]


def _segment_boxes(
    width: int, height: int, boxes: list[BoxPrompt], max_masks: int
) -> list[Prediction]:
    masks = [
        _ellipse_mask(
            shape=(height, width),
            center=((box.x_min + box.x_max) / 2, (box.y_min + box.y_max) / 2),
            radii=((box.x_max - box.x_min) / 2, (box.y_max - box.y_min) / 2),
        )
        for box in boxes
    ]
    if max_masks == 1:
        masks = [np.logical_or.reduce(masks)]
    return [Prediction(mask=mask, score=FAKE_SCORE, class_name=None) for mask in masks]


def _segment_points(width: int, height: int, points: list[PointPrompt]) -> list[Prediction]:
    positives = [point for point in points if point.positive]
    if not positives:
        return []
    radius = _radius(width=width, height=height)
    centroid_x = float(np.mean([point.x for point in positives]))
    centroid_y = float(np.mean([point.y for point in positives]))
    mask = _ellipse_mask(
        shape=(height, width),
        center=(centroid_x, centroid_y),
        radii=(radius, radius),
    )
    for point in points:
        if not point.positive:
            mask &= ~_ellipse_mask(
                shape=(height, width),
                center=(point.x, point.y),
                radii=(radius / 2, radius / 2),
            )
    return [Prediction(mask=mask, score=FAKE_SCORE, class_name=None)]


def _radius(width: int, height: int) -> float:
    return 0.1 * min(width, height)


def _ellipse_mask(
    shape: tuple[int, int], center: tuple[float, float], radii: tuple[float, float]
) -> NDArray[np.bool_]:
    """Returns a filled ellipse mask.

    Args:
        shape: Mask shape (H, W).
        center: Ellipse center (x, y) in pixels.
        radii: Ellipse radii (x, y) in pixels.

    Returns:
        Mask of shape (H, W) and dtype `np.bool_`.
    """
    ys, xs = np.ogrid[: shape[0], : shape[1]]
    center_x, center_y = center
    radius_x = max(radii[0], 0.5)
    radius_y = max(radii[1], 0.5)
    distance = ((xs - center_x) / radius_x) ** 2 + ((ys - center_y) / radius_y) ** 2
    mask: NDArray[np.bool_] = distance <= 1.0
    return mask
