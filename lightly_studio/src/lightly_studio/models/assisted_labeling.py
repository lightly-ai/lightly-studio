"""API models for assisted labeling."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import pydantic
from pydantic import BaseModel, StringConstraints
from pydantic_core import PydanticCustomError


class AssistedLabelingStatusView(BaseModel):
    """State of assisted labeling.

    Attributes:
        unavailable_reason: None if assisted labeling is usable, else the reason why not.
    """

    unavailable_reason: str | None


NormalizedCoordinate = Annotated[float, pydantic.Field(ge=0, le=1, allow_inf_nan=False)]
_NORMALIZED_UPPER_BOUND = 1.000001
MAX_INTERACTIVE_POINTS = 100
DEFAULT_MAX_INSTANCES = 16
MAX_INSTANCES_LIMIT = 32
MAX_INSTANCES_BOXES = 100
MAX_INSTANCES_TEXT_PROMPT_LENGTH = 200

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
            or self.x + self.width > _NORMALIZED_UPPER_BOUND
            or self.y + self.height > _NORMALIZED_UPPER_BOUND
        ):
            raise PydanticCustomError(
                "invalid_box", "The normalized box is empty or outside the image."
            )
        return self


class InteractiveAnnotationRequest(BaseModel):
    """Request for a single-object preview from points or boxes."""

    collection_id: UUID
    sample_id: UUID
    points: list[AnnotationPoint] | None = pydantic.Field(
        default=None, min_length=1, max_length=MAX_INTERACTIVE_POINTS
    )
    # One box, because the preview is a single object
    boxes: list[AnnotationBox] | None = pydantic.Field(default=None, min_length=1, max_length=1)

    @pydantic.model_validator(mode="after")
    def validate_prompts(self) -> InteractiveAnnotationRequest:  # noqa: N804
        """Requires exactly one prompt type and at least one positive point."""
        if (self.points is None) == (self.boxes is None):
            raise PydanticCustomError(
                "invalid_prompts", "Provide either points or boxes, but not both."
            )
        if self.points is not None and not any(point.positive for point in self.points):
            raise PydanticCustomError("invalid_prompts", "Place at least one positive point.")
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


class InteractiveAnnotationResponse(BaseModel):
    """Single-object preview, or None if the provider finds no object."""

    prediction: AnnotationPreview | None


class InstancesAnnotationRequest(BaseModel):
    """Request for previews of all instances that match a text prompt.

    Attributes:
        text_prompt: What to find, for example a class name.
        boxes: Optional examples of instances that the text prompt can miss.
        max_instances: Maximum number of previews.
    """

    collection_id: UUID
    sample_id: UUID
    text_prompt: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=1, max_length=MAX_INSTANCES_TEXT_PROMPT_LENGTH
        ),
    ]
    boxes: list[AnnotationBox] | None = pydantic.Field(
        default=None, min_length=1, max_length=MAX_INSTANCES_BOXES
    )
    max_instances: int = pydantic.Field(default=DEFAULT_MAX_INSTANCES, ge=1, le=MAX_INSTANCES_LIMIT)


class InstancesAnnotationResponse(BaseModel):
    """Instance previews sorted by descending score."""

    predictions: list[AnnotationPreview]
