import { derived, type Readable } from 'svelte/store';
import type { HistogramData } from '$lib/components/Histogram';
import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
import type { MetadataInfo } from '$lib/services/types';

/**
 * Maps each numeric metadata key to its value-distribution histogram.
 * Fields without a histogram (strings, booleans, empty fields) are omitted.
 */
export const selectDistributions = (
    metadataInfo: MetadataInfo[]
): Record<string, HistogramData> => {
    const distributions: Record<string, HistogramData> = {};
    for (const info of metadataInfo) {
        if (info.histogram) {
            distributions[info.name] = {
                binEdges: info.histogram.bin_edges,
                counts: info.histogram.counts
            };
        }
    }
    return distributions;
};

/**
 * Exposes the value-distribution histograms of all numeric metadata fields of
 * a collection, keyed by metadata name.
 *
 * The bins come from the metadata info endpoint (`GET
 * /collections/{id}/metadata/info`); passing `collectionId` triggers that
 * fetch if it hasn't happened yet (it is shared with `useMetadataFilters` and
 * only runs once per collection).
 */
export const useNumericMetadataDistribution = (
    collectionId?: string
): { distributions: Readable<Record<string, HistogramData>> } => {
    const { metadataInfo } = useMetadataFilters(collectionId);
    const distributions = derived(metadataInfo, ($metadataInfo) =>
        selectDistributions($metadataInfo)
    );
    return { distributions };
};
