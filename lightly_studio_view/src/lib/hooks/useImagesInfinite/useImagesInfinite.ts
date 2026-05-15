import type { InfiniteData } from '@tanstack/svelte-query';
import { createInfiniteQuery, infiniteQueryOptions, useQueryClient } from '@tanstack/svelte-query';
import type { ReadImagesError, ReadImagesResponse } from '$lib/api/lightly_studio_local';
import { readImages, type ReadImagesRequest } from '$lib/api/lightly_studio_local';
import { createMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
import { GRID_PAGE_SIZE } from '$lib/constants';
import { getAnnotationsFilter } from './getAnnotationsFilter';
import type { ImagesInfiniteParams, SamplesQueryKey } from './types';

export type { ImagesInfiniteParams } from './types';

// Create infinite query options for samples with mode-aware logic.
const createImagesInfiniteOptions = (params: ImagesInfiniteParams) => {
    // Build query key with intelligent structure to minimize refetches.
    const queryKey: SamplesQueryKey = [
        'readImagesInfinite',
        params.collection_id,
        params.mode,
        params.mode === 'normal' ? params.filters : params.classifierSamples,
        {
            metadata_values: params.metadata_values,
            text_embedding: params.text_embedding
        },
        params.sort_by
    ];

    return infiniteQueryOptions<
        ReadImagesResponse,
        ReadImagesError,
        InfiniteData<ReadImagesResponse>,
        SamplesQueryKey,
        number
    >({
        queryKey,
        queryFn: async ({ pageParam = 0, signal }) => {
            const requestBody = buildRequestBody(params, pageParam);

            const { data } = await readImages({
                path: { collection_id: params.collection_id },
                body: requestBody,
                signal,
                throwOnError: true
            });
            return data;
        },
        initialPageParam: 0,
        getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
        enabled: isQueryEnabled(params)
    });
};

export const buildRequestBody = (
    params: ImagesInfiniteParams,
    pageParam: number
): ReadImagesRequest => {
    const baseBody: ReadImagesRequest = {
        pagination: {
            offset: pageParam,
            limit: GRID_PAGE_SIZE
        },
        text_embedding: params.text_embedding,
        sort_by: params.sort_by ?? undefined,
        filters: {
            sample_filter: {
                query_expr: params.query_expr ?? undefined,
                metadata_filters: params.metadata_values
                    ? createMetadataFilters(params.metadata_values)
                    : undefined
            }
        }
    };

    if (params.mode === 'classifier' && params.classifierSamples) {
        const allSampleIds = [
            ...params.classifierSamples.positiveSampleIds,
            ...params.classifierSamples.negativeSampleIds
        ];

        return {
            ...baseBody,
            sample_ids: allSampleIds
        };
    } else if (params.mode === 'normal' && params.filters) {
        return {
            ...baseBody,
            filters: {
                ...baseBody.filters,
                sample_filter: {
                    ...(baseBody.filters?.sample_filter ?? {}),
                    annotations_filter: getAnnotationsFilter(params.filters),
                    tag_ids: params.filters.tag_ids?.length ? params.filters.tag_ids : undefined,
                    sample_ids: params.filters.sample_ids?.length
                        ? params.filters.sample_ids
                        : undefined
                },
                // TODO(Malte, 10/2025): Share the width/height mapping with useImageFilters to avoid drift.
                width: params.filters.dimensions
                    ? {
                          min: params.filters.dimensions.min_width,
                          max: params.filters.dimensions.max_width
                      }
                    : undefined,
                height: params.filters.dimensions
                    ? {
                          min: params.filters.dimensions.min_height,
                          max: params.filters.dimensions.max_height
                      }
                    : undefined
            }
        };
    }

    return baseBody;
};

const isQueryEnabled = (params: ImagesInfiniteParams): boolean => {
    if (params.mode === 'classifier') {
        // For classifier mode, classifier samples need to exist (even if empty arrays)
        // This ensures the query runs and can show the empty state
        return Boolean(params.classifierSamples);
    }

    // Normal mode is always enabled (return all samples if no filters).
    return true;
};

export const useImagesInfinite = (params: ImagesInfiniteParams) => {
    const samplesOptions = createImagesInfiniteOptions(params);
    const samples = createInfiniteQuery(samplesOptions);
    const client = useQueryClient();

    const refresh = () => {
        client.invalidateQueries({ queryKey: samplesOptions.queryKey });
    };

    return {
        samples,
        refresh
    };
};
