/**
 * Bin-based distribution of a numeric field.
 *
 * `binEdges` has length `counts.length + 1`; bin `i` covers the half-open
 * interval `[binEdges[i], binEdges[i + 1])` (the last bin includes its right
 * edge). Mirrors the backend `HistogramView` model.
 */
export interface HistogramData {
    binEdges: number[];
    counts: number[];
}

/** Inclusive value range used to highlight the selected bins. */
export interface HistogramRange {
    min: number;
    max: number;
}
