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

export const empty: HistogramData = {
    binEdges: [],
    counts: []
};

export const skewed: HistogramData = {
    binEdges: Array.from({ length: 21 }, (_, i) => i * 0.05),
    counts: [120, 80, 52, 34, 22, 15, 10, 7, 5, 4, 3, 2, 2, 1, 1, 1, 0, 0, 0, 1]
};
