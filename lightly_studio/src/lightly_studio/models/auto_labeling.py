"""Wire and Studio API models for the auto-labeling prototype."""

from __future__ import annotations

from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from lightly_studio.resolvers.grid_filter import GridFilter

Probability = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Task = Literal["object_detection", "segmentation"]
NORMALIZED_BOUND_TOLERANCE = 1.000001


class AnnotationLimits(BaseModel):
    """Advertised request limits."""

    max_batch_size: int = Field(gt=0)
    max_request_bytes: int = Field(gt=0)


class AnnotationDescriptor(BaseModel):
    """Model identity and discovered capabilities."""

    protocol_version: Literal["1.0"]
    model_key: str = Field(min_length=1)
    ready: bool
    capabilities: list[str]
    supported_conditioning: list[Literal["targets", "points", "boxes"]]
    limits: AnnotationLimits
    classes: list[str] | None = None


class AnnotationDescriptorView(AnnotationDescriptor):
    """Discovery response including the configured endpoint."""

    endpoint: str


class AnnotationTarget(BaseModel):
    """A model prompt and its destination annotation class."""

    prompt: str = Field(min_length=1)
    class_name: str = Field(min_length=1)


class AnnotationPoint(BaseModel):
    """A normalized positive or negative point."""

    x: Probability
    y: Probability
    positive: bool


class AnnotationBox(BaseModel):
    """A normalized XYWH box used as interactive conditioning."""

    x: Probability
    y: Probability
    width: Probability
    height: Probability

    @model_validator(mode="after")
    def validate_box(self) -> AnnotationBox:  # noqa: N804
        """Reject empty boxes and geometry outside the image."""
        if (
            self.width <= 0
            or self.height <= 0
            or self.x + self.width > NORMALIZED_BOUND_TOLERANCE
            or self.y + self.height > NORMALIZED_BOUND_TOLERANCE
        ):
            raise ValueError("The normalized conditioning box is invalid.")
        return self


class PredictionBase(BaseModel):
    """Common model prediction fields."""

    class_name: str
    score: Probability


class BoxPrediction(PredictionBase):
    """Normalized XYWH object detection."""

    kind: Literal["object_detection"]
    bbox: tuple[Probability, Probability, Probability, Probability]

    @model_validator(mode="after")
    def validate_box(self) -> BoxPrediction:  # noqa: N804
        """Reject empty boxes and geometry outside the image."""
        x, y, width, height = self.bbox
        if (
            width <= 0
            or height <= 0
            or x + width > NORMALIZED_BOUND_TOLERANCE
            or y + height > NORMALIZED_BOUND_TOLERANCE
        ):
            raise ValueError("The model returned an invalid normalized bounding box.")
        return self


class MaskPrediction(PredictionBase):
    """Full-resolution row-major mask, starting with a background run."""

    kind: Literal["segmentation_mask"]
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)
    encoding: Literal["rle"]
    rle: list[Annotated[int, Field(ge=0, strict=True)]]

    @model_validator(mode="after")
    def validate_runs(self) -> MaskPrediction:  # noqa: N804
        """Require exactly one full image of pixels."""
        if sum(self.rle) != self.image_width * self.image_height:
            raise ValueError("The model mask runs do not match its image dimensions.")
        return self


class ClassificationPrediction(PredictionBase):
    """Reserved classification prediction."""

    kind: Literal["classification"]


Prediction = Annotated[
    Union[BoxPrediction, MaskPrediction, ClassificationPrediction], Field(discriminator="kind")
]


class AnnotationResponse(BaseModel):
    """Nested results aligned to the successfully processed inputs."""

    model_key: str
    kept_indices: list[Annotated[int, Field(ge=0, strict=True)]]
    results: list[list[Prediction]]


class AutoLabelBatchRequest(BaseModel):
    """Filter-scoped synchronous auto-labeling run."""

    collection_id: UUID
    filter: GridFilter
    task: Task
    targets: list[AnnotationTarget] = Field(min_length=1)
    confidence_threshold: Probability


class AutoLabelBatchResponse(BaseModel):
    """Run destination and coverage summary."""

    source_id: UUID
    source_name: str
    annotations_created: int
    images_processed: int
    images_skipped: int
    unmatched_prompts: list[str]


class InteractiveAnnotationRequest(BaseModel):
    """Stateless image inference with point or box conditioning."""

    collection_id: UUID
    sample_id: UUID
    points: list[AnnotationPoint] | None = Field(default=None, min_length=1)
    boxes: list[AnnotationBox] | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_conditioning(self) -> InteractiveAnnotationRequest:  # noqa: N804
        """Require exactly one valid conditioning type."""
        if (self.points is None) == (self.boxes is None):
            raise ValueError("Provide either points or boxes, but not both.")
        if self.points is not None and not any(point.positive for point in self.points):
            raise ValueError("Place at least one positive point.")
        return self


class AnnotationPreviewBox(BaseModel):
    """Absolute integer XYWH geometry."""

    x: int
    y: int
    width: int
    height: int


class AnnotationPreview(BaseModel):
    """Uncommitted bbox-cropped segmentation preview."""

    bbox: AnnotationPreviewBox
    segmentation_mask: list[int]
    score: float
    class_name: str


class InteractiveAnnotationResponse(BaseModel):
    """Preview and measured model-call latency."""

    prediction: AnnotationPreview | None
    latency_ms: float
