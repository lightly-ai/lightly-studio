/**
 * Types for the ConfusionMatrix component.
 *
 * The endpoint shape mirrors the Pydantic `ConfusionMatrix` model in
 * lightly_studio/src/lightly_studio/models/evaluation_confusion_matrix.py
 * (shipped via LIG-9514).
 */

export const NO_GROUND_TRUTH_ROW_LABEL = '(no ground truth)';
export const NO_PREDICTION_COL_LABEL = '(no prediction)';

export interface ConfusionMatrix {
    row_labels: string[];
    col_labels: string[];
    counts: number[][];
}
