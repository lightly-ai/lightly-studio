"""Dense confusion-matrix payloads for evaluation runs."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

# Row label for predictions with no matching ground truth (false positives).
NO_GROUND_TRUTH_ROW_LABEL = "(no ground truth)"

# Column label for ground truths with no matching prediction (false negatives).
NO_PREDICTION_COL_LABEL = "(no prediction)"


class ConfusionCell(BaseModel):
    """A single class-by-class cell of a confusion matrix for one evaluation run.

    Identifies samples that contain a ground-truth/prediction annotation pairing of
    the given label combination. Labels are matched by name (unique per dataset), so
    no annotation-id lookup is needed when resolving the cell to its samples.

    Attributes:
        evaluation_run_id: Evaluation run whose pairing metrics are queried.
        gt_label: Ground-truth annotation label name (matrix row).
        pred_label: Prediction annotation label name (matrix column).
    """

    evaluation_run_id: UUID = Field(
        description="Evaluation run whose pairing metrics define the cell.",
    )
    gt_label: str = Field(description="Ground-truth annotation label name (matrix row).")
    pred_label: str = Field(description="Prediction annotation label name (matrix column).")


class ConfusionMatrix(BaseModel):
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
