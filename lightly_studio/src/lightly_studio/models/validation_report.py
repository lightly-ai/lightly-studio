"""Models for the dataset annotation-validation report."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class BoxIssue(BaseModel):
    """A single flagged object-detection box.

    Attributes:
        sample_id: ID of the image the box belongs to.
        annotation_id: ID of the flagged annotation.
    """

    sample_id: UUID
    annotation_id: UUID


class ValidationReport(BaseModel):
    """Integrity problems found in a dataset's object-detection annotations.

    Attributes:
        degenerate_boxes: Boxes with a non-positive width or height.
        out_of_bounds_boxes: Boxes that extend past the image bounds.
    """

    degenerate_boxes: list[BoxIssue]
    out_of_bounds_boxes: list[BoxIssue]
