import type { ConfusionMatrix } from '../../types';
import { SENTINELS } from '../constants/constants';

/** Real class labels, excluding the sentinel no-GT/no-prediction rows. */
export function getRealClasses(matrix: ConfusionMatrix): string[] {
    return matrix.row_labels.filter((label) => !SENTINELS.has(label));
}
