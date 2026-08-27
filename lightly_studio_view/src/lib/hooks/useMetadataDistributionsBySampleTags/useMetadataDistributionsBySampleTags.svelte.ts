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
import { selectCategoricalDistributions } from '$lib/hooks/useCategoricalMetadataDistribution/useCategoricalMetadataDistribution.svelte';
import { selectDistributions } from '$lib/hooks/useNumericMetadataDistribution/useNumericMetadataDistribution';

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

export interface SampleTagMetadataDistributions {
    id: string;
    label: string;
    histograms: ReturnType<typeof selectDistributions>;
    categorical: ReturnType<typeof selectCategoricalDistributions>;
}

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

export const useMetadataDistributionsBySampleTags = (getParams: () => MetadataComparisonParams) =>
    createQueries(() => {
        const { collectionId, sampleTags, filter, binCount, enabled = true } = getParams();
        const queries = sampleTags.flatMap(({ id }) => {
            const tagFilter = withSampleTagFilter(filter, id);
            const histogramBody = {
                filters: tagFilter,
                ...(binCount ? { bin_count: binCount } : {})
            };
            return [
                {
                    ...getMetadataHistogramsOptions({
                        path: { collection_id: collectionId },
                        body: histogramBody
                    }),
                    enabled: enabled && sampleTags.length > 0,
                    placeholderData: (previous: Record<string, HistogramView> | undefined) =>
                        previous
                },
                {
                    ...getMetadataValueCountsOptions({
                        path: { collection_id: collectionId },
                        body: { filters: tagFilter }
                    }),
                    enabled: enabled && sampleTags.length > 0,
                    placeholderData: (
                        previous: Record<string, MetadataValueCountsView> | undefined
                    ) => previous
                }
            ];
        });

        return {
            queries,
            combine: (results) => ({
                data: sampleTags.flatMap((tag, index): SampleTagMetadataDistributions[] => {
                    const histograms = results[index * 2]?.data as
                        | Record<string, HistogramView>
                        | undefined;
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
                error: results.find((result) => result.error)?.error
            })
        };
    });
