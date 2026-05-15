import type { InfiniteData } from '@tanstack/svelte-query';
import { infiniteQueryOptions } from '@tanstack/svelte-query';
import type { ReadImagesError, ReadImagesResponse } from '$lib/api/lightly_studio_local';
import { readImages } from '$lib/api/lightly_studio_local';
import { buildRequestBody } from './buildRequestBody';
import type { ImagesInfiniteParams, SamplesQueryKey } from './types';

// Create infinite query options for samples with mode-aware logic.
export const createImagesInfiniteOptions = (params: ImagesInfiniteParams) => {
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
        enabled: params.mode !== 'classifier' || Boolean(params.classifierSamples)
    });
};
