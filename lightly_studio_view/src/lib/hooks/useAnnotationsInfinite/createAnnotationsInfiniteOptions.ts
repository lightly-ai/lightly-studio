import type { InfiniteData } from '@tanstack/svelte-query';
import { infiniteQueryOptions } from '@tanstack/svelte-query';
import {
    readAnnotationsWithPayload,
    type AnnotationWithPayloadAndCountView,
    type ReadAnnotationsWithPayloadError
} from '$lib/api/lightly_studio_local';
import { buildRequestBody } from './buildRequestBody';
import type { AnnotationsInfiniteParams, AnnotationsInfiniteQueryKey } from './types';

export const createAnnotationsInfiniteOptions = (params: AnnotationsInfiniteParams) => {
    const queryKey: AnnotationsInfiniteQueryKey = [
        'readAnnotationsWithPayloadInfinite',
        params.collection_id,
        {
            annotation_label_ids: params.annotation_label_ids,
            tag_ids: params.tag_ids,
            sample_ids: params.sample_ids,
            text_embedding: params.text_embedding,
            limit: params.limit
        }
    ];

    return infiniteQueryOptions<
        AnnotationWithPayloadAndCountView,
        ReadAnnotationsWithPayloadError,
        InfiniteData<AnnotationWithPayloadAndCountView>,
        AnnotationsInfiniteQueryKey,
        number
    >({
        queryKey,
        queryFn: async ({ pageParam = 0, signal }) => {
            const { data } = await readAnnotationsWithPayload({
                path: { collection_id: params.collection_id },
                body: buildRequestBody(params, pageParam),
                signal,
                throwOnError: true
            });
            return data;
        },
        initialPageParam: 0,
        getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined
    });
};
