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

interface MetadataComparisonField {
    name: string;
    type: 'numeric' | 'categorical';
}

interface MetadataComparisonParams {
    collectionId: string;
    sampleTags: SampleTagItem[];
    filter?: ImageFilter;
    binCount?: number;
    field?: MetadataComparisonField;
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
 * Selected metadata distribution for each selected sample tag.
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
                combineSampleTagResults(params.sampleTags, results, params.field)
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

/** Build one request per selected tag for the visible metadata field. */
const buildSampleTagQueries = ({
    collectionId,
    sampleTags,
    filter,
    binCount,
    field,
    enabled = true
}: MetadataComparisonParams) => {
    if (!field) return [];

    return sampleTags.map(({ id }) => {
        const body = {
            filters: withSampleTagFilter(filter, id),
            fields: [field.name]
        };
        return {
            ...(field.type === 'numeric'
                ? getMetadataHistogramsOptions({
                      path: { collection_id: collectionId },
                      body: { ...body, ...(binCount ? { bin_count: binCount } : {}) }
                  })
                : getMetadataValueCountsOptions({
                      path: { collection_id: collectionId },
                      body
                  })),
            enabled
        };
    });
};

/**
 * Pairs each tag with its result. A tag whose request has not resolved is
 * dropped rather than rendered as an empty series, so one failing tag does not
 * discard the data of the tags that did return.
 */
const combineSampleTagResults = (
    sampleTags: SampleTagItem[],
    results: MetadataQueryResult[],
    field?: MetadataComparisonField
): {
    data: SampleTagMetadataDistributions[];
    isFetching: boolean;
    error: Error | null;
} => ({
    data: sampleTags.flatMap((tag, index): SampleTagMetadataDistributions[] => {
        const response = results[index]?.data;
        if (!response || !field) return [];

        return [
            {
                ...tag,
                histograms:
                    field.type === 'numeric'
                        ? selectDistributions(response as Record<string, HistogramView>)
                        : {},
                categorical:
                    field.type === 'categorical'
                        ? selectCategoricalDistributions(
                              response as Record<string, MetadataValueCountsView>
                          )
                        : {}
            }
        ];
    }),
    isFetching: results.some((result) => result.isFetching),
    error: results.find((result) => result.error)?.error ?? null
});
