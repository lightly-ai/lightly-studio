"""Dense confusion-matrix payloads for object-detection evaluation runs.

Synthetic axis labels ``NO_GROUND_TRUTH_ROW_LABEL`` and ``NO_PREDICTION_COL_LABEL``

mark false-positive and false-negative buckets when aggregating

``evaluation_annotation_metric`` rows into a label-by-label matrix.

"""

from __future__ import annotations

from pydantic import BaseModel, Field

# Row label for predictions with no matching ground truth (false positives).
NO_GROUND_TRUTH_ROW_LABEL = "(no ground truth)"

# Column label for ground truths with no matching prediction (false negatives).
NO_PREDICTION_COL_LABEL = "(no prediction)"


class ObjectDetectionConfusionMatrix(BaseModel):
    """Confusion matrix built from ``evaluation_annotation_metric`` rows.

    Each persisted pairing outcome (TP, FP, or FN) increments one cell. Rows follow
    ground-truth context (class labels, plus a synthetic row for FPs). Columns follow
    prediction context (class labels, plus a synthetic column for FNs).

    Attributes:
        row_labels: Ground-truth axis labels (sorted classes, then optional FP row).
        col_labels: Prediction axis labels (sorted classes, then optional FN column).
        counts: Integer cell counts; ``counts[i][j]`` is ``row_labels[i]`` vs ``col_labels[j]``.

    """

    row_labels: list[str] = Field(
        description="Ground-truth axis labels, sorted real classes then optional "
        f"'{NO_GROUND_TRUTH_ROW_LABEL}' row when false positives exist.",
    )

    col_labels: list[str] = Field(
        description="Prediction axis labels, sorted real classes then optional "
        f"'{NO_PREDICTION_COL_LABEL}' column when false negatives exist.",
    )

    counts: list[list[int]] = Field(
        description="Integer counts; ``counts[i][j]`` is row_labels[i] vs col_labels[j].",
    )
