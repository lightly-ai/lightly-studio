import type { ConfusionMatrix } from '../../types';
import { SENTINELS } from '../constants/constants';

/** Computes total off-diagonal mass per real class (used for confusion-based ranking). */
export function computeConfusionScores(matrix: ConfusionMatrix): Map<string, number> {
    const scores = new Map<string, number>();
    for (let i = 0; i < matrix.row_labels.length; i++) {
        for (let j = 0; j < matrix.col_labels.length; j++) {
            const row = matrix.row_labels[i];
            const col = matrix.col_labels[j];
            const count = matrix.counts[i][j];
            if (row === col || count <= 0) continue;
            if (!SENTINELS.has(row)) scores.set(row, (scores.get(row) ?? 0) + count);
            if (!SENTINELS.has(col)) scores.set(col, (scores.get(col) ?? 0) + count);
        }
    }
    return scores;
}
