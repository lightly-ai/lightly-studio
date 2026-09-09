import type { InfiniteData } from '@tanstack/svelte-query';
import { infiniteQueryOptions } from '@tanstack/svelte-query';
import type { ReadImagesError, ReadImagesResponse } from '$lib/api/lightly_studio_local';
import { readImages } from '$lib/api/lightly_studio_local';
import { createMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
import { buildRequestBody } from './buildRequestBody';
import type { ImagesInfiniteParams, SamplesQueryKey } from './types';

export const getImagesInfiniteQueryKeyPrefix = (collectionId: string) =>
    ['readImagesInfinite', collectionId] as const;

// Create infinite query options for samples with mode-aware logic.
export const createImagesInfiniteOptions = (params: ImagesInfiniteParams) => {
    // Key on the effective metadata filters, not the raw slider state.
    // When /metadata/info resolves it seeds every numeric field's value to its full
    // range (min/max), which leaves the request unchanged because a full-range
    // value emits no filter.
    // Keying on the raw values would flip the key from `{}` to the seeded ranges
    // and spawn a new query that re-enters loading for an identical request.
    const metadataFilters = createMetadataFilters(
        params.metadata_values ?? {},
        params.categorical_metadata_values ?? {}
    );

    // Build query key with intelligent structure to minimize refetches.
    const queryKey: SamplesQueryKey = [
        ...getImagesInfiniteQueryKeyPrefix(params.collection_id),
        params.mode,
        params.mode === 'normal' ? params.filters : params.classifierSamples,
        {
            metadata_filters: metadataFilters,
            text_embedding: params.text_embedding,
            query_expr: params.query_expr
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
        enabled: params.mode !== 'classifier' || Boolean(params.classifierSamples)
    });
};
