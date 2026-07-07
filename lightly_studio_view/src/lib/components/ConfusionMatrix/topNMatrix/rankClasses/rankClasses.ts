import type { ConfusionMatrix } from '../../types';
import { computeConfusionScores } from '../computeConfusionScores/computeConfusionScores';
import { getRealClasses } from '../getRealClasses/getRealClasses';
import { type ClassSortOption } from '../types';
import { rankClassesByConfusion } from '../rankClassesByConfusion/rankClassesByConfusion';
import { rankClassesByGroundTruthSamples } from '../rankClassesByGroundTruthSamples/rankClassesByGroundTruthSamples';

/** Ranks real classes by the given sort criterion. */
export function rankClasses(matrix: ConfusionMatrix, sortBy: ClassSortOption): string[] {
    switch (sortBy) {
        case 'most-confused':
            return rankClassesByConfusion(matrix);
        case 'least-confused': {
            const scores = computeConfusionScores(matrix);
            return getRealClasses(matrix).sort(
                (a, b) => (scores.get(a) ?? 0) - (scores.get(b) ?? 0)
            );
        }
        case 'most-samples':
            return rankClassesByGroundTruthSamples(matrix);
        case 'alphabetical':
            return [...getRealClasses(matrix)].sort((a, b) => a.localeCompare(b));
    }
}
