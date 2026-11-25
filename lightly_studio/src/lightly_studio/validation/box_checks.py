"""Pure object-detection box integrity checks.

Each check takes bounding boxes and returns the annotation IDs of the boxes that
fail it. The checks do no I/O so they are cheap to unit test.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from lightly_studio.evaluation.object_detection_metric import BoundingBox


def find_degenerate_boxes(boxes: Sequence[BoundingBox]) -> list[UUID]:
    """Return the annotation IDs of boxes with a non-positive width or height."""
    return [box.annotation_id for box in boxes if box.width <= 0 or box.height <= 0]


def find_out_of_bounds_boxes(
    boxes: Sequence[BoundingBox], image_width: int, image_height: int
) -> list[UUID]:
    """Return the annotation IDs of boxes that extend past the image bounds.

    A box that ends exactly on the right or bottom edge (``x + width == image_width``)
    is in bounds, because the pixel range ``[x, x + width)`` is half-open.
    """
    return [
        box.annotation_id
        for box in boxes
        if box.x < 0
        or box.y < 0
        or box.x + box.width > image_width
        or box.y + box.height > image_height
    ]
