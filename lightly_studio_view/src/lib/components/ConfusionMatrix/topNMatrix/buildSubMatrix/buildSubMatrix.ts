import {
    NO_GROUND_TRUTH_ROW_LABEL,
    NO_PREDICTION_COL_LABEL,
    type ConfusionMatrix
} from '../../types';
import { OTHER_LABEL } from '../constants/constants';
import { getRealClasses } from '../getRealClasses/getRealClasses';

/**
 * Builds a sub-matrix containing only `visibleClasses` (in original order).
 * Hidden classes are aggregated into an "(other)" row/column so totals are
 * preserved. Sentinel rows/columns are always kept.
 */
export function buildSubMatrix(matrix: ConfusionMatrix, visibleClasses: string[]): ConfusionMatrix {
    if (matrix.row_labels.length === 0) return matrix;

    const visible = new Set(visibleClasses);
    const real = getRealClasses(matrix);
    const kept = real.filter((label) => visible.has(label));
    const hasOther = kept.length < real.length;

    const rowLabels = [...kept, ...(hasOther ? [OTHER_LABEL] : []), NO_GROUND_TRUTH_ROW_LABEL];
    const colLabels = [...kept, ...(hasOther ? [OTHER_LABEL] : []), NO_PREDICTION_COL_LABEL];

    // Index only the kept classes and sentinels — never the aggregate label — so a
    // real class named OTHER_LABEL cannot collide with the aggregate bucket. Any
    // input label absent from the map is a hidden class and routes to otherIdx.
    const rowIndex = new Map<string, number>(kept.map((label, i) => [label, i]));
    rowIndex.set(NO_GROUND_TRUTH_ROW_LABEL, rowLabels.length - 1);
    const colIndex = new Map<string, number>(kept.map((label, i) => [label, i]));
    colIndex.set(NO_PREDICTION_COL_LABEL, colLabels.length - 1);

    const otherRowIdx = hasOther ? kept.length : -1;
    const otherColIdx = hasOther ? kept.length : -1;

    const counts = rowLabels.map(() => colLabels.map(() => 0));
    for (let i = 0; i < matrix.row_labels.length; i++) {
        const outRow = rowIndex.get(matrix.row_labels[i]) ?? otherRowIdx;
        for (let j = 0; j < matrix.col_labels.length; j++) {
            const outCol = colIndex.get(matrix.col_labels[j]) ?? otherColIdx;
            counts[outRow][outCol] += matrix.counts[i][j];
        }
    }
    return { row_labels: rowLabels, col_labels: colLabels, counts };
}
