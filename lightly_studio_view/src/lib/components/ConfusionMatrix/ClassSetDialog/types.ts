import type { ClassSortOption } from '../topNMatrix';

/** How the visible class set is chosen (Voxel51-style configure dialog). */
export interface ClassSetConfig {
    /** Which tab decides the visible set: ranked top-N or an explicit manual list. */
    mode: 'topN' | 'manual';
    /** Number of classes to keep when `mode === 'topN'`. Ignored in manual mode. */
    n: number;
    /** Ranking criterion used to pick the top-N. Ignored in manual mode. */
    sortBy: ClassSortOption;
    /** Explicit class labels to keep when `mode === 'manual'`. Ignored in top-N mode. */
    manualClasses: string[];
}

/** Coloring options configured in the same dialog. */
export interface ColorConfig {
    /** Multiplier applied to the color scale; higher values saturate cells faster. */
    intensity: number;
    /** When true, map counts through a logarithmic scale so small counts stay visible next to large ones. */
    logScale: boolean;
}
