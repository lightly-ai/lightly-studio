import { createQuery } from '@tanstack/svelte-query';
import type { HistogramView, ImageFilter } from '$lib/api/lightly_studio_local';
import { getMetadataHistogramsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getMetadataHistograms } from '$lib/api/lightly_studio_local/sdk.gen';
import type { HistogramData } from '$lib/components/Histogram';

/**
 * Maps the endpoint response (metadata key → HistogramView) to the shape the
 * `Histogram` component consumes.
 */
export const selectDistributions = (
    histograms: Record<string, HistogramView> | undefined
): Record<string, HistogramData> => {
    const distributions: Record<string, HistogramData> = {};
    for (const [key, histogram] of Object.entries(histograms ?? {})) {
        distributions[key] = {
            binEdges: histogram.bin_edges,
            counts: histogram.counts
        };
    }
    return distributions;
};

/**
 * Queries the value-distribution histograms of all numeric metadata fields of
 * a collection, keyed by metadata name.
 *
 * The bins come from `POST /collections/{id}/metadata/histograms`: bin edges
 * span the full collection so the axis stays stable, while the counts respect
 * the given filters (each key's own metadata filter is excluded server-side,
 * faceted-search style). Pass the same `ImageFilter` that drives the grid so
 * the histograms track the active view; the query refetches whenever the
 * filter changes.
 */
export const useNumericMetadataDistribution = ({
    collectionId,
    filter
}: {
    collectionId: string;
    filter?: ImageFilter;
}) => {
    const requestOptions = {
        path: { collection_id: collectionId },
        ...(filter ? { body: { filters: filter } } : {})
    } as const;

    const options = getMetadataHistogramsOptions(requestOptions);

    return createQuery(() => ({
        ...options,
        // Keep the previous bars on screen while a filter change refetches.
        placeholderData: (previous: Record<string, HistogramView> | undefined) => previous,
        queryFn: async ({ signal }: { signal: AbortSignal }) => {
            const { data } = await getMetadataHistograms({
                ...requestOptions,
                signal,
                throwOnError: true
            });
            return data;
        }
    }));
};
