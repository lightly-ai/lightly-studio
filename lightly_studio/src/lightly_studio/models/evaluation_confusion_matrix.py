"""Dense confusion-matrix payloads for object-detection evaluation runs."""

from __future__ import annotations

from pydantic import BaseModel, Field

# Row label for predictions with no matching ground truth (false positives).
NO_GROUND_TRUTH_ROW_LABEL = "(no ground truth)"

# Column label for ground truths with no matching prediction (false negatives).
NO_PREDICTION_COL_LABEL = "(no prediction)"


class ObjectDetectionConfusionMatrix(BaseModel):
    """Confusion matrix built from ``evaluation_annotation_metric`` rows.

    Each persisted pairing outcome (TP, FP, or FN) increments one cell. Rows follow
    ground-truth context (class labels, plus the synthetic FP row). Columns follow
    prediction context (class labels, plus the synthetic FN column). The synthetic
    axes are always present (with zero counts when unused).

    Attributes:
        row_labels: Ground-truth axis labels (sorted classes, then the FP row).
        col_labels: Prediction axis labels (sorted classes, then the FN column).
        counts: Integer cell counts; ``counts[i][j]`` is ``row_labels[i]`` vs ``col_labels[j]``.

    """

    row_labels: list[str] = Field(
        description="Ground-truth axis labels, sorted real classes then the "
        f"'{NO_GROUND_TRUTH_ROW_LABEL}' row (always present, zero-filled when no FPs).",
    )

    col_labels: list[str] = Field(
        description="Prediction axis labels, sorted real classes then the "
        f"'{NO_PREDICTION_COL_LABEL}' column (always present, zero-filled when no FNs).",
    )

    counts: list[list[int]] = Field(
        description="Integer counts; ``counts[i][j]`` is row_labels[i] vs col_labels[j].",
    )
