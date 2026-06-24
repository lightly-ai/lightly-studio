import type { ConfusionMatrix } from '../../types';
import { SENTINELS } from '../constants/constants';
import { getRealClasses } from '../getRealClasses/getRealClasses';

/** Ranks real classes by total ground-truth sample count, descending. */
export function rankClassesByGroundTruthSamples(matrix: ConfusionMatrix): string[] {
    const gtCounts = new Map<string, number>();
    for (let i = 0; i < matrix.row_labels.length; i++) {
        const label = matrix.row_labels[i];
        if (SENTINELS.has(label)) continue;
        gtCounts.set(
            label,
            matrix.counts[i].reduce((a, b) => a + Math.max(b, 0), 0)
        );
    }
    return getRealClasses(matrix).sort((a, b) => (gtCounts.get(b) ?? 0) - (gtCounts.get(a) ?? 0));
}
