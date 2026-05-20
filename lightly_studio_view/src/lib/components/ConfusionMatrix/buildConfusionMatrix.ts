import {
    NO_GROUND_TRUTH_ROW_LABEL,
    NO_PREDICTION_COL_LABEL,
    type AnnotationPairing,
    type ConfusionMatrix,
    type Thresholds
} from './types';

/**
 * Recompute a dense confusion matrix from per-pairing annotations and
 * user-controlled thresholds. Used by the prototype's slider story so the
 * matrix updates without a network round-trip.
 *
 * Filter semantics (mirror the backend's intended OD eval logic):
 * - `confidence < thresholds.confidence` → the prediction is suppressed.
 *   If the pairing also had ground truth, it becomes a false negative
 *   (gt vs `(no prediction)`). If there was no ground truth either, the
 *   pairing drops entirely.
 * - `iou < thresholds.iou` (and both sides have a label) → the match is
 *   broken: the prediction becomes a false positive
 *   (`(no ground truth)` vs pred), the ground truth becomes a false
 *   negative (gt vs `(no prediction)`).
 *
 * Output mirrors the LIG-9514 dense shape: sorted real class names on
 * both axes, with the synthetic FP row and FN column always appended
 * unless there are no pairings at all (then all three fields are empty).
 */
export function buildConfusionMatrix(
    pairings: AnnotationPairing[],
    thresholds: Thresholds
): ConfusionMatrix {
    type Bucket = { gt: string | null; pred: string | null };
    const buckets: Bucket[] = [];

    for (const pairing of pairings) {
        const confidenceOk =
            pairing.confidence === null || pairing.confidence >= thresholds.confidence;
        const iouOk = pairing.iou === null || pairing.iou >= thresholds.iou;

        const gt = pairing.gt_label;
        const pred = confidenceOk ? pairing.pred_label : null;

        if (!iouOk && gt !== null && pred !== null) {
            buckets.push({ gt: null, pred });
            buckets.push({ gt, pred: null });
            continue;
        }
        if (gt === null && pred === null) continue;
        buckets.push({ gt, pred });
    }

    if (buckets.length === 0) {
        return { row_labels: [], col_labels: [], counts: [] };
    }

    const realLabels = new Set<string>();
    for (const bucket of buckets) {
        if (bucket.gt !== null) realLabels.add(bucket.gt);
        if (bucket.pred !== null) realLabels.add(bucket.pred);
    }
    const sortedRealLabels = [...realLabels].sort();
    const row_labels = [...sortedRealLabels, NO_GROUND_TRUTH_ROW_LABEL];
    const col_labels = [...sortedRealLabels, NO_PREDICTION_COL_LABEL];

    const rowIndex = new Map(row_labels.map((label, index) => [label, index]));
    const colIndex = new Map(col_labels.map((label, index) => [label, index]));

    const counts: number[][] = row_labels.map(() => col_labels.map(() => 0));
    for (const bucket of buckets) {
        const rowKey = bucket.gt ?? NO_GROUND_TRUTH_ROW_LABEL;
        const colKey = bucket.pred ?? NO_PREDICTION_COL_LABEL;
        const r = rowIndex.get(rowKey);
        const c = colIndex.get(colKey);
        if (r === undefined || c === undefined) continue;
        counts[r][c] += 1;
    }

    return { row_labels, col_labels, counts };
}
