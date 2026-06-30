/**
 * Types for the ConfusionMatrix component.
 *
 */

export const NO_GROUND_TRUTH_ROW_LABEL = '(no ground truth)';
export const NO_PREDICTION_COL_LABEL = '(no prediction)';

export interface ConfusionMatrix {
    row_labels: string[];
    col_labels: string[];
    counts: number[][];
}

/**
 * A cell resolved from a confusion-matrix click: a real class-by-class cell, the
 * false-positive bucket (`NO_GROUND_TRUTH_ROW_LABEL` × real class), or the
 * false-negative bucket (real class × `NO_PREDICTION_COL_LABEL`).
 */
export interface ConfusionCellSelection {
    /** Ground-truth label (matrix row), or `NO_GROUND_TRUTH_ROW_LABEL` for the FP bucket. */
    gtLabel: string;
    /** Prediction label (matrix column), or `NO_PREDICTION_COL_LABEL` for the FN bucket. */
    predLabel: string;
}
