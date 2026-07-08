import type { InfiniteData } from '@tanstack/svelte-query';
import { infiniteQueryOptions } from '@tanstack/svelte-query';
import {
    readAnnotationsWithPayload,
    type AnnotationWithPayloadAndCountView,
    type ReadAnnotationsWithPayloadError
} from '$lib/api/lightly_studio_local';
import type { AnnotationsInfiniteParams, AnnotationsInfiniteQueryKey } from './types';

const DEFAULT_PAGE_LIMIT = 100;

export const createAnnotationsInfiniteOptions = (params: AnnotationsInfiniteParams) => {
    const queryKey: AnnotationsInfiniteQueryKey = [
        'readAnnotationsWithPayloadInfinite',
        params.collection_id,
        {
            annotation_label_ids: params.annotation_label_ids,
            tag_ids: params.tag_ids,
            sample_ids: params.sample_ids,
            embedding_region: params.embedding_region,
            text_embedding: params.text_embedding
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
                body: {
                    pagination: { cursor: pageParam, limit: DEFAULT_PAGE_LIMIT },
                    annotation_label_ids: params.annotation_label_ids,
                    tag_ids: params.tag_ids,
                    sample_ids: params.sample_ids,
                    embedding_region: params.embedding_region,
                    text_embedding: params.text_embedding
                },
                signal,
                throwOnError: true
            });
            return data;
        },
        initialPageParam: 0,
        getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined
    });
};
