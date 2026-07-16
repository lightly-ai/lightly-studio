import type { HistogramData } from './types';

/** Roughly normal distribution over [0, 100], 20 bins. */
export const normal: HistogramData = {
    binEdges: Array.from({ length: 21 }, (_, i) => i * 5),
    counts: [1, 2, 4, 7, 12, 19, 28, 38, 46, 50, 50, 46, 38, 28, 19, 12, 7, 4, 2, 1]
};

/** All values identical — the backend collapses this to a single bin. */
export const singleBin: HistogramData = {
    binEdges: [42, 42],
    counts: [3]
};
