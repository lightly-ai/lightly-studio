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

export interface NumericMetadataHistogramOptions {
    collectionId: string;
    filter?: ImageFilter;
    binCount?: number;
    /** Restrict the response to these numeric metadata fields. */
    fields?: string[];
}

export const getNumericMetadataHistogramRequestOptions = ({
    collectionId,
    filter,
    binCount,
    fields
}: NumericMetadataHistogramOptions) => ({
    path: { collection_id: collectionId },
    ...(filter || binCount || fields
        ? {
              body: {
                  ...(filter ? { filters: filter } : {}),
                  ...(binCount ? { bin_count: binCount } : {}),
                  ...(fields ? { fields } : {})
              }
          }
        : {})
});

/**
 * Queries value-distribution histograms of a collection's numeric metadata
 * fields, keyed by metadata name. Pass `fields` to request only visible fields.
 *
 * The bins come from {@link https://github.com/lightly-ai/lightly-studio/blob/main/lightly_studio/src/lightly_studio/api/routes/api/metadata.py `POST /collections/{id}/metadata/histograms`}: bin edges
 * span the full collection so the axis stays stable, while the counts respect
 * the given filters (each key's own metadata filter is excluded server-side,
 * faceted-search style). Pass the same `ImageFilter` that drives the grid so
 * the histograms track the active view; the query refetches whenever the
 * filter changes.
 *
 * Accepts a reactive factory function (same pattern as `useImageAnnotationCounts`)
 * so that `collectionId`, `filter`, `binCount`, and `enabled` are re-read inside the
 * TanStack Query reactive context on every change.
 *
 * @param getOptions - Factory returning the query options. Called reactively by
 *   TanStack Query whenever any reactive dependency inside it changes.
 */
export const useNumericMetadataDistribution = (
    getOptions: () => {
        collectionId: string;
        filter?: ImageFilter;
        /** Number of equal-width bins per histogram (server default: 20). */
        binCount?: number;
        /** Restrict the response to these numeric metadata fields. */
        fields?: string[];
        enabled?: boolean;
    }
) =>
    createQuery(() => {
        const { collectionId, filter, binCount, fields, enabled = true } = getOptions();
        // Computed inside the reactive function so a change to collectionId,
        // filter, binCount, or fields updates the query key and triggers a refetch.
        const requestOptions = getNumericMetadataHistogramRequestOptions({
            collectionId,
            filter,
            binCount,
            fields
        });
        return {
            ...getMetadataHistogramsOptions(requestOptions),
            enabled,
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
