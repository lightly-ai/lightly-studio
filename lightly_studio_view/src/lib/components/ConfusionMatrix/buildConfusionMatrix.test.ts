import { describe, expect, it } from 'vitest';
import { buildConfusionMatrix } from './buildConfusionMatrix';
import {
    NO_GROUND_TRUTH_ROW_LABEL,
    NO_PREDICTION_COL_LABEL,
    type AnnotationPairing
} from './types';

const thresholds = { confidence: 0.25, iou: 0.5 };

function findCount(
    matrix: ReturnType<typeof buildConfusionMatrix>,
    rowLabel: string,
    colLabel: string
): number {
    const r = matrix.row_labels.indexOf(rowLabel);
    const c = matrix.col_labels.indexOf(colLabel);
    if (r === -1 || c === -1) return 0;
    return matrix.counts[r][c];
}

describe('buildConfusionMatrix', () => {
    it('returns an empty matrix when there are no pairings', () => {
        const matrix = buildConfusionMatrix([], thresholds);
        expect(matrix).toEqual({ row_labels: [], col_labels: [], counts: [] });
    });

    it('always appends the synthetic FP row and FN column when non-empty', () => {
        const pairings: AnnotationPairing[] = [
            { gt_label: 'car', pred_label: 'car', confidence: 0.9, iou: 0.8 }
        ];
        const matrix = buildConfusionMatrix(pairings, thresholds);
        expect(matrix.row_labels).toEqual(['car', NO_GROUND_TRUTH_ROW_LABEL]);
        expect(matrix.col_labels).toEqual(['car', NO_PREDICTION_COL_LABEL]);
    });

    it('counts a perfect match as a TP on the diagonal', () => {
        const pairings: AnnotationPairing[] = [
            { gt_label: 'car', pred_label: 'car', confidence: 0.9, iou: 0.8 },
            { gt_label: 'car', pred_label: 'car', confidence: 0.7, iou: 0.6 }
        ];
        const matrix = buildConfusionMatrix(pairings, thresholds);
        expect(findCount(matrix, 'car', 'car')).toBe(2);
    });

    it('counts a label mismatch as an off-diagonal cell', () => {
        const pairings: AnnotationPairing[] = [
            { gt_label: 'car', pred_label: 'person', confidence: 0.9, iou: 0.8 }
        ];
        const matrix = buildConfusionMatrix(pairings, thresholds);
        expect(findCount(matrix, 'car', 'person')).toBe(1);
    });

    it('places ground-truth-only pairings in the FN column', () => {
        const pairings: AnnotationPairing[] = [
            { gt_label: 'car', pred_label: null, confidence: null, iou: null }
        ];
        const matrix = buildConfusionMatrix(pairings, thresholds);
        expect(findCount(matrix, 'car', NO_PREDICTION_COL_LABEL)).toBe(1);
    });

    it('places prediction-only pairings in the FP row', () => {
        const pairings: AnnotationPairing[] = [
            { gt_label: null, pred_label: 'car', confidence: 0.9, iou: null }
        ];
        const matrix = buildConfusionMatrix(pairings, thresholds);
        expect(findCount(matrix, NO_GROUND_TRUTH_ROW_LABEL, 'car')).toBe(1);
    });

    it('suppresses a prediction when confidence is below threshold', () => {
        const pairings: AnnotationPairing[] = [
            { gt_label: 'car', pred_label: 'car', confidence: 0.1, iou: 0.9 }
        ];
        const matrix = buildConfusionMatrix(pairings, thresholds);
        expect(findCount(matrix, 'car', 'car')).toBe(0);
        expect(findCount(matrix, 'car', NO_PREDICTION_COL_LABEL)).toBe(1);
    });

    it('drops a no-GT pairing entirely when confidence suppresses the prediction', () => {
        const pairings: AnnotationPairing[] = [
            { gt_label: null, pred_label: 'car', confidence: 0.1, iou: null }
        ];
        const matrix = buildConfusionMatrix(pairings, thresholds);
        expect(matrix.row_labels).toEqual([]);
        expect(matrix.col_labels).toEqual([]);
    });

    it('breaks a low-IoU match into a separate FP and FN', () => {
        const pairings: AnnotationPairing[] = [
            { gt_label: 'car', pred_label: 'car', confidence: 0.9, iou: 0.2 }
        ];
        const matrix = buildConfusionMatrix(pairings, thresholds);
        expect(findCount(matrix, 'car', 'car')).toBe(0);
        expect(findCount(matrix, NO_GROUND_TRUTH_ROW_LABEL, 'car')).toBe(1);
        expect(findCount(matrix, 'car', NO_PREDICTION_COL_LABEL)).toBe(1);
    });

    it('sorts real labels alphabetically and pushes sentinels to the end', () => {
        const pairings: AnnotationPairing[] = [
            { gt_label: 'zebra', pred_label: 'zebra', confidence: 0.9, iou: 0.8 },
            { gt_label: 'ant', pred_label: 'ant', confidence: 0.9, iou: 0.8 },
            { gt_label: 'mouse', pred_label: 'mouse', confidence: 0.9, iou: 0.8 }
        ];
        const matrix = buildConfusionMatrix(pairings, thresholds);
        expect(matrix.row_labels).toEqual(['ant', 'mouse', 'zebra', NO_GROUND_TRUTH_ROW_LABEL]);
        expect(matrix.col_labels).toEqual(['ant', 'mouse', 'zebra', NO_PREDICTION_COL_LABEL]);
    });

    it('aggregates counts across many pairings without losing data', () => {
        const pairings: AnnotationPairing[] = [
            ...Array(5).fill({ gt_label: 'car', pred_label: 'car', confidence: 0.9, iou: 0.8 }),
            ...Array(3).fill({ gt_label: 'car', pred_label: 'person', confidence: 0.9, iou: 0.8 }),
            ...Array(2).fill({ gt_label: null, pred_label: 'car', confidence: 0.9, iou: null }),
            ...Array(4).fill({ gt_label: 'person', pred_label: null, confidence: null, iou: null })
        ];
        const matrix = buildConfusionMatrix(pairings, thresholds);
        const total = matrix.counts.flat().reduce((sum, n) => sum + n, 0);
        expect(total).toBe(14);
        expect(findCount(matrix, 'car', 'car')).toBe(5);
        expect(findCount(matrix, 'car', 'person')).toBe(3);
        expect(findCount(matrix, NO_GROUND_TRUTH_ROW_LABEL, 'car')).toBe(2);
        expect(findCount(matrix, 'person', NO_PREDICTION_COL_LABEL)).toBe(4);
    });

    it('treats null confidence as passing the threshold', () => {
        const pairings: AnnotationPairing[] = [
            { gt_label: 'car', pred_label: 'car', confidence: null, iou: 0.9 }
        ];
        const matrix = buildConfusionMatrix(pairings, thresholds);
        expect(findCount(matrix, 'car', 'car')).toBe(1);
    });
});
