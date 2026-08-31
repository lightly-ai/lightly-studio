import { createQueries } from '@tanstack/svelte-query';
import type {
    HistogramView,
    ImageFilter,
    MetadataValueCountsView
} from '$lib/api/lightly_studio_local';
import {
    getMetadataHistogramsOptions,
    getMetadataValueCountsOptions
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { selectCategoricalDistributions } from '$lib/hooks/useCategoricalMetadataDistribution';
import { selectDistributions } from '$lib/hooks/useNumericMetadataDistribution';

interface SampleTagItem {
    id: string;
    label: string;
}

interface MetadataComparisonParams {
    collectionId: string;
    sampleTags: SampleTagItem[];
    filter?: ImageFilter;
    binCount?: number;
    enabled?: boolean;
}

/** The subset of a query result this hook reads, so `combine` can be extracted. */
interface MetadataQueryResult {
    data?: unknown;
    isFetching: boolean;
    error: Error | null;
}

export interface SampleTagMetadataDistributions {
    id: string;
    label: string;
    histograms: ReturnType<typeof selectDistributions>;
    categorical: ReturnType<typeof selectCategoricalDistributions>;
}

/**
 * Numeric and categorical metadata distributions for each selected sample tag.
 *
 * The panel renders these next to the current view's own distribution, so each
 * tag is queried with the current exploration filter narrowed to that tag - the
 * rest of the filter is preserved and the tags never leak back into it.
 */
export const useMetadataDistributionsBySampleTags = (getParams: () => MetadataComparisonParams) =>
    createQueries(() => {
        const params = getParams();
        return {
            queries: buildSampleTagQueries(params),
            combine: (results: MetadataQueryResult[]) =>
                combineSampleTagResults(params.sampleTags, results)
        };
    });

/** Replaces the filter's tag scope, leaving the rest of the exploration filter. */
export const withSampleTagFilter = (
    filter: ImageFilter | undefined,
    tagId: string
): ImageFilter => ({
    ...filter,
    sample_filter: {
        ...filter?.sample_filter,
        tag_ids: [tagId]
    }
});

/** Two requests per tag - one per metadata response shape - in tag order. */
const buildSampleTagQueries = ({
    collectionId,
    sampleTags,
    filter,
    binCount,
    enabled = true
}: MetadataComparisonParams) =>
    sampleTags.flatMap(({ id }) => {
        const body = { filters: withSampleTagFilter(filter, id) };
        return [
            {
                ...getMetadataHistogramsOptions({
                    path: { collection_id: collectionId },
                    body: { ...body, ...(binCount ? { bin_count: binCount } : {}) }
                }),
                enabled: enabled && sampleTags.length > 0,
                placeholderData: (previous: Record<string, HistogramView> | undefined) => previous
            },
            {
                ...getMetadataValueCountsOptions({
                    path: { collection_id: collectionId },
                    body
                }),
                enabled: enabled && sampleTags.length > 0,
                placeholderData: (previous: Record<string, MetadataValueCountsView> | undefined) =>
                    previous
            }
        ];
    });

/**
 * Pairs each tag with its two results. A tag whose requests have not resolved is
 * dropped rather than rendered as an empty series, so one failing tag does not
 * discard the data of the tags that did return.
 */
const combineSampleTagResults = (
    sampleTags: SampleTagItem[],
    results: MetadataQueryResult[]
): {
    data: SampleTagMetadataDistributions[];
    isFetching: boolean;
    error: Error | null;
} => ({
    data: sampleTags.flatMap((tag, index): SampleTagMetadataDistributions[] => {
        const histograms = results[index * 2]?.data as Record<string, HistogramView> | undefined;
        const categorical = results[index * 2 + 1]?.data as
            | Record<string, MetadataValueCountsView>
            | undefined;
        if (!histograms && !categorical) return [];
        return [
            {
                ...tag,
                histograms: selectDistributions(histograms),
                categorical: selectCategoricalDistributions(categorical)
            }
        ];
    }),
    isFetching: results.some((result) => result.isFetching),
    error: results.find((result) => result.error)?.error ?? null
});
