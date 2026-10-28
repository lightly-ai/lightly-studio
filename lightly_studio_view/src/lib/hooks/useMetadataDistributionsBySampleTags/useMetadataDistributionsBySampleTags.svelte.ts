import { createQueries } from '@tanstack/svelte-query';
import type {
    HistogramView,
    MetadataHistogramsRequest,
    MetadataValueCountsView
} from '$lib/api/lightly_studio_local';
import {
    getImageHistogramsOptions,
    getMetadataHistogramsOptions,
    getMetadataValueCountsOptions
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { selectCategoricalDistributions } from '$lib/hooks/useCategoricalMetadataDistribution';
import {
    getImageFieldHistogramRequestOptions,
    selectImageFieldDistributions,
    type ImageField
} from '$lib/hooks/useImageFieldDistribution';
import { selectDistributions } from '$lib/hooks/useNumericMetadataDistribution';

interface SampleTagItem {
    id: string;
    label: string;
}

/** A user metadata key, or an image field such as the width. */
type MetadataComparisonField =
    | { name: string; type: 'numeric' | 'categorical' }
    | { name: ImageField; type: 'image' };

/** An image or video filter, tagged with its `filter_type`. */
type MetadataDistributionFilter = NonNullable<MetadataHistogramsRequest['filters']>;

interface MetadataComparisonParams {
    collectionId: string;
    sampleTags: SampleTagItem[];
    filter?: MetadataDistributionFilter;
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

/**
 * Replaces the filter's tag scope, leaving the rest of the exploration filter.
 * Without a filter, the result is an image filter.
 */
export const withSampleTagFilter = (
    filter: MetadataDistributionFilter | undefined,
    tagId: string
): MetadataDistributionFilter => ({
    filter_type: 'image',
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
        if (field.type === 'image') {
            const tagFilter = withSampleTagFilter(filter, id);
            return {
                ...getImageHistogramsOptions(
                    getImageFieldHistogramRequestOptions({
                        collectionId,
                        filter: tagFilter.filter_type === 'image' ? tagFilter : undefined,
                        binCount,
                        fields: [field.name]
                    })
                ),
                enabled
            };
        }
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
                      body: { ...body, limit: null }
                  })),
            enabled
        };
    });
};

/** Histograms keyed by distribution group ID. */
const selectHistograms = (field: MetadataComparisonField, response: unknown) => {
    if (field.type === 'image') {
        return selectImageFieldDistributions(response as Record<string, HistogramView>);
    }
    if (field.type === 'numeric') {
        return selectDistributions(response as Record<string, HistogramView>);
    }
    return {};
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
                histograms: selectHistograms(field, response),
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
