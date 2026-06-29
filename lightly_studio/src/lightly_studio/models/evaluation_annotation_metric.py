"""EvaluationAnnotationMetricTable model — unified annotation pairing and metrics."""

from __future__ import annotations

from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlmodel import Field, SQLModel

from lightly_studio.models.annotation.annotation_base import (
    AnnotationView,
    ImageAnnotationView,
)


class EvaluationAnnotationMetricTable(SQLModel, table=True):
    """One row per annotation pair produced by an evaluation run.

    Match type is derivable from the nullable ID columns:
    - both IDs set  → TP
    - only pred set → FP
    - only gt set   → FN
    """

    __tablename__ = "evaluation_annotation_metric"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    evaluation_run_id: UUID = Field(foreign_key="evaluation_run.id", index=True)
    sample_id: UUID = Field(foreign_key="sample.sample_id", index=True)
    pred_annotation_id: UUID | None = Field(
        default=None,
        foreign_key="annotation_base.sample_id",
        index=True,
    )
    gt_annotation_id: UUID | None = Field(
        default=None,
        foreign_key="annotation_base.sample_id",
        index=True,
    )
    metric_name: str | None = Field(default=None, index=True)
    value: float | None = Field(default=None)


class EvaluationAnnotationMetricCreate(SQLModel):
    """Evaluation annotation metric payload used when creating new rows."""

    evaluation_run_id: UUID
    sample_id: UUID
    pred_annotation_id: UUID | None = None
    gt_annotation_id: UUID | None = None
    metric_name: str | None = None
    value: float | None = None


class EvaluationMatchType(str, Enum):
    """Per-annotation pairing outcome for an object-detection evaluation run.

    Derived from the nullable id columns on ``evaluation_annotation_metric``:
    - both ids set  → ``tp`` (true positive)
    - only pred set → ``fp`` (false positive)
    - only gt set   → ``fn`` (false negative)
    """

    TP = "tp"
    FP = "fp"
    FN = "fn"


class EvaluationMatchSortField(str, Enum):
    """Primary ordering applied to a list of evaluation matches.

    - ``iou``: order by IoU. Only true positives carry one, so false positives
      and false negatives are pushed to the end. This is the default view.
    - ``confidence``: order by the prediction confidence. False negatives have no
      prediction, so they are pushed to the end.
    """

    IOU = "iou"
    CONFIDENCE = "confidence"


class EvaluationMatchView(BaseModel):
    """A single evaluation match enriched with the boxes that produced it.

    A true positive carries both the ground-truth and prediction annotations
    (plus the IoU that paired them). False positives carry only the prediction;
    false negatives carry only the ground truth.
    """

    model_config = ConfigDict(populate_by_name=True)

    match_type: EvaluationMatchType
    iou: float | None = None
    gt_annotation: AnnotationView | None = None
    pred_annotation: AnnotationView | None = None
    parent_sample_data: ImageAnnotationView


class EvaluationMatchesWithCountView(BaseModel):
    """Response model for a paginated list of evaluation matches."""

    model_config = ConfigDict(populate_by_name=True)

    matches: list[EvaluationMatchView] = PydanticField(..., alias="data")
    total_count: int
    next_cursor: int | None = PydanticField(None, alias="nextCursor")
