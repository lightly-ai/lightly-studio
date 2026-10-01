import type { HistogramData, HistogramSeries } from '$lib/components/Histogram';

export interface HistogramComparison {
    id: string;
    label: string;
    histograms: Record<string, HistogramData>;
}

/**
 * The named histograms the comparison tags contribute for a metadata key.
 *
 * A tag whose request has not resolved, or that holds no value for the key,
 * contributes nothing rather than an all-zero series - an empty bar row reads
 * as "no samples", which is a different statement from "not loaded yet".
 */
export const buildTagHistogramSeries = (
    comparisons: HistogramComparison[],
    metadataKey: string
): HistogramSeries[] =>
    comparisons.flatMap(({ id, label, histograms }) => {
        const data = histograms[metadataKey];
        return data ? [{ id, label, data }] : [];
    });
