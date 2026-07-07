import type { ConfusionMatrix } from '../types';
import { getRealClasses, rankClasses } from '../topNMatrix';
import type { ClassSetConfig } from '../ClassSetDialog/types';

/**
 * Resolves which real classes should be visible for the given config, in the
 * matrix's original label order. Top-N mode keeps the highest-ranked `n`
 * classes; manual mode keeps the explicitly selected labels.
 */
export function selectVisibleClasses(matrix: ConfusionMatrix, config: ClassSetConfig): string[] {
    const baseClasses =
        config.mode === 'topN'
            ? rankClasses(matrix, config.sortBy).slice(0, config.n)
            : config.manualClasses;
    return getRealClasses(matrix).filter((c) => baseClasses.includes(c));
}
