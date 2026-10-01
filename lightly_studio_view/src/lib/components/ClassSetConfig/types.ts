/**
 * The class-selection portion of a chart config, shared between the confusion
 * matrix and the distribution panel. `TSort` is the host chart's own sort-option
 * union (ranking criteria for the matrix, count/name for the distribution).
 */
export interface ClassSetSelection<TSort extends string = string> {
    /** Which control decides the visible set: ranked top-N or an explicit manual list. */
    mode: 'topN' | 'manual';
    /** Number of classes kept when `mode === 'topN'`. Ignored in manual mode. */
    n: number;
    /** Ranking criterion used to pick the top-N. Ignored in manual mode. */
    sortBy: TSort;
    /** Explicit class labels kept when `mode === 'manual'`. Ignored in top-N mode. */
    manualClasses: string[];
}
