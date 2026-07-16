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

export function buildImageAnnotationCountsQueryKey({
    annotationType,
    countMode,
    queryKeyOverride
}: {
    annotationType?: AnnotationType;
    countMode?: AnnotationCountMode;
    // unknown[] intentionally: callers may extend the base key with extra
    // segments (e.g. [...baseKey, 'distribution']). The cast bridges this to
    // the specific tuple type createQuery expects.
    queryKeyOverride?: unknown[];
}): ReturnType<typeof countImageAnnotationsByCollectionQueryKey> {
    if (queryKeyOverride) {
        return [
            ...queryKeyOverride,
            ...(annotationType ? [annotationType] : []),
            ...(countMode ? [countMode] : [])
        ] as ReturnType<typeof countImageAnnotationsByCollectionQueryKey>;
    }
    if (annotationType || countMode) {
        return countImageAnnotationsByCollectionQueryKey({
            path: { collection_id: '__static_value__' },
            body: {
                ...(annotationType ? { annotation_type: annotationType } : {}),
                ...(countMode ? { count_mode: countMode } : {})
            }
        });
    }
    return useImageAnnotationCountsQueryKey;
}

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
        const queryKey = buildImageAnnotationCountsQueryKey({
            annotationType,
            countMode,
            queryKeyOverride
        });

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
            // Keep showing previous data while the new key's request is in-flight
            // so the panel doesn't flash empty during a count_mode transition.
            placeholderData: (
                previousData: Array<{ [key: string]: string | number }> | undefined
            ) => previousData,
            ...(enabled !== undefined ? { enabled } : {})
        };
    });
};
