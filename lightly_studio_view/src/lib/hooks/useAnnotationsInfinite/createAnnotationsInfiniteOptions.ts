import type { InfiniteData } from '@tanstack/svelte-query';
import { infiniteQueryOptions } from '@tanstack/svelte-query';
import {
    readAnnotationsWithPayload,
    type AnnotationWithPayloadAndCountView,
    type ReadAnnotationsWithPayloadError
} from '$lib/api/lightly_studio_local';
import type { AnnotationsInfiniteParams, AnnotationsInfiniteQueryKey } from './types';

const DEFAULT_PAGE_LIMIT = 100;

export const getAnnotationsInfiniteQueryKeyPrefix = (collectionId: string) =>
    ['readAnnotationsWithPayloadInfinite', collectionId] as const;

export const createAnnotationsInfiniteOptions = (params: AnnotationsInfiniteParams) => {
    const queryKey: AnnotationsInfiniteQueryKey = [
        ...getAnnotationsInfiniteQueryKeyPrefix(params.collection_id),
        {
            annotation_label_ids: params.annotation_label_ids,
            tag_ids: params.tag_ids,
            sample_ids: params.sample_ids,
            embedding_region: params.embedding_region,
            text_embedding: params.text_embedding,
            // Part of the cache key, not only the body: omitting it here serves cached
            // pages and the grid refuses to reorder.
            sort_by: params.sort_by
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
                    text_embedding: params.text_embedding,
                    sort_by: params.sort_by
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
