import { createQuery } from '@tanstack/svelte-query';
import type { HistogramView, ImageFilter } from '$lib/api/lightly_studio_local';
import { getMetadataHistogramsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getMetadataHistograms } from '$lib/api/lightly_studio_local/sdk.gen';
import type { HistogramData } from '$lib/components/Histogram';

/**
 * Maps the endpoint response (metadata key → HistogramView) to the shape the
 * `Histogram` component consumes.
 *
 * @param histograms - Raw API response keyed by metadata field name, or
 *   `undefined` while the query is loading.
 */
export const selectDistributions = (
    histograms: Record<string, HistogramView> | undefined
): Record<string, HistogramData> =>
    Object.fromEntries(
        Object.entries(histograms ?? {}).map(([key, { bin_edges, counts }]) => [
            key,
            { binEdges: bin_edges, counts }
        ])
    );

/**
 * Queries the value-distribution histograms of all numeric metadata fields of
 * a collection, keyed by metadata name.
 *
 * The bins come from {@link https://github.com/lightly-ai/lightly-studio/blob/main/lightly_studio/src/lightly_studio/api/routes/api/metadata.py `POST /collections/{id}/metadata/histograms`}: bin edges
 * span the full collection so the axis stays stable, while the counts respect
 * the given filters (each key's own metadata filter is excluded server-side,
 * faceted-search style). Pass the same `ImageFilter` that drives the grid so
 * the histograms track the active view; the query refetches whenever the
 * filter changes.
 *
 * @param collectionId - ID of the collection whose metadata distributions to load.
 * @param filter - Active image filter; counts in each histogram reflect this
 *   filter (the key's own metadata filter is excluded server-side). The query
 *   refetches automatically when this value changes.
 */
export const useNumericMetadataDistribution = ({
    collectionId,
    filter
}: {
    collectionId: string;
    filter?: ImageFilter;
}) =>
    createQuery(() => {
        // Computed inside the reactive function so a change to collectionId or
        // filter updates the query key and triggers a refetch.
        const requestOptions = {
            path: { collection_id: collectionId },
            ...(filter ? { body: { filters: filter } } : {})
        };
        return {
            ...getMetadataHistogramsOptions(requestOptions),
            select: selectDistributions,
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
        };
    });
