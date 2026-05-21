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
