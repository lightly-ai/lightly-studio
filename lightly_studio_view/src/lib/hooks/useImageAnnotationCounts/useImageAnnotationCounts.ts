import { createQuery } from '@tanstack/svelte-query';
import type {
    AnnotationCountMode,
    AnnotationType,
    ImageFilter
} from '$lib/api/lightly_studio_local';
import {
    countImageAnnotationsByCollectionOptions,
    countImageAnnotationsByCollectionQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { countImageAnnotationsByCollection } from '$lib/api/lightly_studio_local/sdk.gen';

export const useImageAnnotationCountsQueryKey = countImageAnnotationsByCollectionQueryKey({
    path: { collection_id: '__static_value__' }
});

export function buildImageAnnotationCountsRequest({
    collectionId,
    filter,
    annotationType,
    countMode
}: {
    collectionId: string;
    filter?: ImageFilter;
    annotationType?: AnnotationType;
    countMode?: AnnotationCountMode;
}) {
    return {
        path: { collection_id: collectionId },
        ...(filter || annotationType || countMode
            ? {
                  body: {
                      ...(filter ? { filter } : {}),
                      ...(annotationType ? { annotation_type: annotationType } : {}),
                      ...(countMode ? { count_mode: countMode } : {})
                  }
              }
            : {})
    };
}

export const useImageAnnotationCounts = (
    getParams: () => {
        collectionId: string;
        filter?: ImageFilter;
        /** Restrict counts to a single annotation type (e.g. classification). */
        annotationType?: AnnotationType;
        /** Controls whether objects or samples are counted. */
        countMode?: AnnotationCountMode;
        /**
         * Override the cache key. Pass a key that is a suffix-extension of
         * `useImageAnnotationCountsQueryKey` so that mutation invalidations still
         * reach this query while avoiding cache collisions with other callers.
         */
        // unknown[] intentionally: callers may extend the base key with extra
        // segments (e.g. [...baseKey, 'distribution']). The cast inside the hook
        // bridges this to the specific tuple type createQuery expects.
        queryKey?: unknown[];
        /** Set to false to prevent the query from fetching. Default: true. */
        enabled?: boolean;
    }
) => {
    return createQuery(() => {
        const {
            collectionId,
            filter,
            annotationType,
            countMode,
            queryKey: queryKeyOverride,
            enabled
        } = getParams();

        const requestOptions = buildImageAnnotationCountsRequest({
            collectionId,
            filter,
            annotationType,
            countMode
        });

        const options = countImageAnnotationsByCollectionOptions(requestOptions);
        // Keep the collection id static so annotation mutations invalidate every
        // variant, but discriminate by annotation type so the per-type queries
        // don't collide in the cache. count_mode is intentionally excluded from
        // the key: when it changes, TanStack Query returns cached data immediately
        // and refetches in the background, preventing sources from disappearing
        // during the mode transition.
        const queryKey =
            (queryKeyOverride as ReturnType<typeof countImageAnnotationsByCollectionQueryKey>) ??
            (annotationType
                ? countImageAnnotationsByCollectionQueryKey({
                      path: { collection_id: '__static_value__' },
                      body: { annotation_type: annotationType }
                  })
                : useImageAnnotationCountsQueryKey);

        return {
            ...options,
            queryKey,
            queryFn: async ({ signal }: { signal: AbortSignal }) => {
                const { data } = await countImageAnnotationsByCollection({
                    ...requestOptions,
                    signal,
                    throwOnError: true
                });
                return data;
            },
            ...(enabled !== undefined ? { enabled } : {})
        };
    });
};
