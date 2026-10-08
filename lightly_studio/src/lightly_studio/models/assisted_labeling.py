"""API models for AI-assisted labeling previews."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from pydantic_core import PydanticCustomError

from lightly_studio.assisted_labeling.provider import OutputType, ProviderCapabilities

NormalizedCoordinate = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
NORMALIZED_BOUND_TOLERANCE = 1.000001
DEFAULT_MAX_INSTANCES = 16


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

    @model_validator(mode="after")
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


class PrepareAnnotationRequest(BaseModel):
    """Request to prepare an image for later preview requests."""

    collection_id: UUID
    sample_id: UUID


class InteractiveAnnotationRequest(BaseModel):
    """Request for a single-object preview from points or boxes."""

    collection_id: UUID
    sample_id: UUID
    points: list[AnnotationPoint] | None = Field(default=None, min_length=1)
    boxes: list[AnnotationBox] | None = Field(default=None, min_length=1)
    output_type: OutputType = OutputType.MASK

    @model_validator(mode="after")
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
        segmentation_mask: Run-length encoding of the mask, cropped to `bbox`.
        score: Confidence score, if the provider returns one.
        class_name: Annotation class name, if the provider returns one.
    """

    bbox: AnnotationPreviewBox
    segmentation_mask: list[int]
    score: float | None
    class_name: str | None


class InteractiveAnnotationResponse(BaseModel):
    """Single-object preview and the latency of the provider call."""

    prediction: AnnotationPreview | None
    latency_ms: float


class InstancesAnnotationRequest(BaseModel):
    """Request for previews of all instances that match a text prompt or boxes."""

    collection_id: UUID
    sample_id: UUID
    prompt: str | None = Field(default=None, min_length=1)
    boxes: list[AnnotationBox] | None = Field(default=None, min_length=1)
    max_instances: int = Field(default=DEFAULT_MAX_INSTANCES, ge=1, le=32)
    output_type: OutputType = OutputType.MASK

    @model_validator(mode="after")
    def validate_prompts(self) -> InstancesAnnotationRequest:  # noqa: N804
        """Requires a non-blank text prompt, boxes, or both."""
        if (self.prompt is None or not self.prompt.strip()) and not self.boxes:
            raise PydanticCustomError("invalid_prompts", "Provide a text prompt, boxes, or both.")
        return self


class InstancesAnnotationResponse(BaseModel):
    """Instance previews sorted by descending score and the latency of the provider call."""

    predictions: list[AnnotationPreview]
    latency_ms: float


class AssistedLabelingProviderView(BaseModel):
    """An assisted labeling provider and its state.

    Attributes:
        provider_id: Stable ID of the provider.
        display_name: Human-readable name of the provider.
        sends_data_to_third_party: True if the provider sends image data to a third party.
        capabilities: Prompt types and limits that the provider supports.
        unavailable_reason: None if the provider is usable, else the reason why not.
    """

    provider_id: str
    display_name: str
    sends_data_to_third_party: bool
    capabilities: ProviderCapabilities
    unavailable_reason: str | None
