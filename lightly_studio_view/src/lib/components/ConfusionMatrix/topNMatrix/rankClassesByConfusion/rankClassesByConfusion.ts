import type { ConfusionMatrix } from '../../types';
import { computeConfusionScores } from '../computeConfusionScores/computeConfusionScores';
import { getRealClasses } from '../getRealClasses/getRealClasses';

/**
 * Ranks real classes by total off-diagonal mass they are involved in
 * (as ground truth or prediction, including no-GT/no-prediction cells).
 */
export function rankClassesByConfusion(matrix: ConfusionMatrix): string[] {
    const scores = computeConfusionScores(matrix);
    return getRealClasses(matrix).sort((a, b) => (scores.get(b) ?? 0) - (scores.get(a) ?? 0));
}
