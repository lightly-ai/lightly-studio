/**
 * Types for the ConfusionMatrix component.
 *
 * The endpoint shape mirrors the Pydantic `ConfusionMatrix` model in
 * lightly_studio/src/lightly_studio/models/evaluation_confusion_matrix.py
 * (shipped via LIG-9514). The `AnnotationPairing` shape is prototype-only:
 * the threshold-slider story drives a client-side recomputation from raw
 * pairings via `buildConfusionMatrix`. See DESIGN.md.
 */

export const NO_GROUND_TRUTH_ROW_LABEL = '(no ground truth)';
export const NO_PREDICTION_COL_LABEL = '(no prediction)';

export interface ConfusionMatrix {
    row_labels: string[];
    col_labels: string[];
    counts: number[][];
}

export interface AnnotationPairing {
    gt_label: string | null;
    pred_label: string | null;
    confidence: number | null;
    iou: number | null;
}

export interface Thresholds {
    confidence: number;
    iou: number;
}

export const DEFAULT_THRESHOLDS: Thresholds = {
    confidence: 0.25,
    iou: 0.5
};

export type ConfusionMatrixDataSource =
    | { kind: 'matrix'; matrix: ConfusionMatrix }
    | { kind: 'pairings'; pairings: AnnotationPairing[]; thresholds: Thresholds };
