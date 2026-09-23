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
    queryKeyOverride,
    ...params
}: Parameters<typeof buildImageAnnotationCountsRequest>[0] & {
    // unknown[] intentionally: callers may extend the base key with extra
    // segments (e.g. [...baseKey, 'distribution']).
    queryKeyOverride?: unknown[];
}): ReturnType<typeof countImageAnnotationsByCollectionQueryKey> {
    // The request is appended to every key, so the cast bridges the longer
    // array to the tuple type createQuery expects.
    return [
        ...(queryKeyOverride ?? useImageAnnotationCountsQueryKey),
        buildImageAnnotationCountsRequest(params)
    ] as unknown as ReturnType<typeof countImageAnnotationsByCollectionQueryKey>;
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
         * Prefix for the cache key. The request is appended to it. Extend
         * `useImageAnnotationCountsQueryKey` so that mutation invalidations still
         * reach this query.
         */
        queryKey?: unknown[];
        /** Set to false to prevent the query from fetching. Default: true. */
        enabled?: boolean;
    }
) => {
    return createQuery(() => {
        const { queryKey: queryKeyOverride, enabled, ...params } = getParams();

        const requestOptions = buildImageAnnotationCountsRequest(params);
        const options = countImageAnnotationsByCollectionOptions(requestOptions);
        const queryKey = buildImageAnnotationCountsQueryKey({ ...params, queryKeyOverride });

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
            // The key changes with the collection, filter and count mode. Keep showing
            // the previous data while the new key's request is in flight so the counts
            // don't flash empty.
            placeholderData: (
                previousData: Array<{ [key: string]: string | number }> | undefined
            ) => previousData,
            ...(enabled !== undefined ? { enabled } : {})
        };
    });
};
