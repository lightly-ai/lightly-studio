"""API models for assisted labeling."""

from __future__ import annotations

from typing import Annotated

import pydantic
from pydantic import BaseModel
from pydantic_core import PydanticCustomError


class AssistedLabelingStatusView(BaseModel):
    """State of assisted labeling.

    Attributes:
        unavailable_reason: None if assisted labeling is usable, else the reason why not.
    """

    unavailable_reason: str | None


NormalizedCoordinate = Annotated[float, pydantic.Field(ge=0, le=1, allow_inf_nan=False)]
NORMALIZED_BOUND_TOLERANCE = 1.000001

# The validators raise `PydanticCustomError` instead of `ValueError`, because the error
# context of a `ValueError` is not JSON serializable in the 422 response.


class AnnotationPoint(BaseModel):
    """A positive or negative point in normalized image coordinates."""

    x: NormalizedCoordinate
    y: NormalizedCoordinate
    positive: bool


class AnnotationBox(BaseModel):
    """A box in normalized XYWH image coordinates."""

    x: NormalizedCoordinate
    y: NormalizedCoordinate
    width: NormalizedCoordinate
    height: NormalizedCoordinate

    @pydantic.model_validator(mode="after")
    def validate_box(self) -> AnnotationBox:  # noqa: N804
        """Rejects empty boxes and boxes outside the image."""
        if (
            self.width <= 0
            or self.height <= 0
            or self.x + self.width > NORMALIZED_BOUND_TOLERANCE
            or self.y + self.height > NORMALIZED_BOUND_TOLERANCE
        ):
            raise PydanticCustomError("invalid_box", "The normalized box is invalid.")
        return self


class AnnotationPreviewBox(BaseModel):
    """A box in absolute integer XYWH pixel coordinates."""

    x: int
    y: int
    width: int
    height: int


class AnnotationPreview(BaseModel):
    """A segmentation mask preview that is not saved.

    Attributes:
        bbox: Bounding box of the mask in pixels.
        segmentation_mask: Full-image row-wise run-length encoding of the mask, in the
            format of the annotation create endpoint.
        score: Confidence score, if the provider returns one.
    """

    bbox: AnnotationPreviewBox
    segmentation_mask: list[int]
    score: float | None
