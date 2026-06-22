import { NO_GROUND_TRUTH_ROW_LABEL, NO_PREDICTION_COL_LABEL, type ConfusionMatrix } from './types';

/**
 * Helpers for LIG-9665: client-side top-N class selection with
 * "(other)" aggregation. Pure functions, no ECharts dependency.
 */

export const OTHER_LABEL = '(other)';

const SENTINELS = new Set<string>([NO_GROUND_TRUTH_ROW_LABEL, NO_PREDICTION_COL_LABEL]);

/** Real class labels, excluding the sentinel no-GT/no-prediction rows. */
export function getRealClasses(matrix: ConfusionMatrix): string[] {
    return matrix.row_labels.filter((label) => !SENTINELS.has(label));
}

/**
 * Ranks real classes by total off-diagonal mass they are involved in
 * (as ground truth or prediction, including no-GT/no-prediction cells).
 */
export function rankClassesByConfusion(matrix: ConfusionMatrix): string[] {
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
    return getRealClasses(matrix).sort((a, b) => (scores.get(b) ?? 0) - (scores.get(a) ?? 0));
}

export type ClassSortOption = 'most-confused' | 'least-confused' | 'most-samples' | 'alphabetical';

export const CLASS_SORT_LABELS: Record<ClassSortOption, string> = {
    'most-confused': 'Most confused',
    'least-confused': 'Least confused',
    'most-samples': 'Most ground truth samples',
    alphabetical: 'Alphabetical'
};

/** How the visible class set is chosen (Voxel51-style configure dialog). */
export interface ClassSetConfig {
    mode: 'topN' | 'manual';
    n: number;
    sortBy: ClassSortOption;
    manualClasses: string[];
}

/** Coloring options configured in the same dialog. */
export interface ColorConfig {
    intensity: number;
    logScale: boolean;
}

/** Ranks real classes by the given sort criterion. */
export function rankClasses(matrix: ConfusionMatrix, sortBy: ClassSortOption): string[] {
    switch (sortBy) {
        case 'most-confused':
            return rankClassesByConfusion(matrix);
        case 'least-confused':
            return rankClassesByConfusion(matrix).reverse();
        case 'most-samples': {
            const gtCounts = new Map<string, number>();
            for (let i = 0; i < matrix.row_labels.length; i++) {
                const label = matrix.row_labels[i];
                if (SENTINELS.has(label)) continue;
                gtCounts.set(
                    label,
                    matrix.counts[i].reduce((a, b) => a + Math.max(b, 0), 0)
                );
            }
            return getRealClasses(matrix).sort(
                (a, b) => (gtCounts.get(b) ?? 0) - (gtCounts.get(a) ?? 0)
            );
        }
        case 'alphabetical':
            return [...getRealClasses(matrix)].sort((a, b) => a.localeCompare(b));
    }
}

/**
 * Builds a sub-matrix containing only `visibleClasses` (in original order).
 * Hidden classes are aggregated into an "(other)" row/column so totals are
 * preserved. Sentinel rows/columns are always kept.
 */
export function buildSubMatrix(matrix: ConfusionMatrix, visibleClasses: string[]): ConfusionMatrix {
    const visible = new Set(visibleClasses);
    const real = getRealClasses(matrix);
    const kept = real.filter((label) => visible.has(label));
    const other = kept.length < real.length ? [OTHER_LABEL] : [];

    const rowLabels = [...kept, ...other, NO_GROUND_TRUTH_ROW_LABEL];
    const colLabels = [...kept, ...other, NO_PREDICTION_COL_LABEL];
    const rowIndex = new Map(rowLabels.map((label, i) => [label, i]));
    const colIndex = new Map(colLabels.map((label, i) => [label, i]));

    const counts = rowLabels.map(() => colLabels.map(() => 0));
    for (let i = 0; i < matrix.row_labels.length; i++) {
        const outRow = rowIndex.get(matrix.row_labels[i]) ?? rowIndex.get(OTHER_LABEL)!;
        for (let j = 0; j < matrix.col_labels.length; j++) {
            const outCol = colIndex.get(matrix.col_labels[j]) ?? colIndex.get(OTHER_LABEL)!;
            counts[outRow][outCol] += matrix.counts[i][j];
        }
    }
    return { row_labels: rowLabels, col_labels: colLabels, counts };
}
