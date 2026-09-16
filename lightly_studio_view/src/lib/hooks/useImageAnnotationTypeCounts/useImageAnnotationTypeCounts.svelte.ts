import { createQuery } from '@tanstack/svelte-query';
import type { ImageFilter } from '$lib/api/lightly_studio_local';
import {
    countImageAnnotationsByTypeOptions,
    countImageAnnotationsByTypeQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { countImageAnnotationsByType } from '$lib/api/lightly_studio_local/sdk.gen';

export const useImageAnnotationTypeCountsQueryKey = countImageAnnotationsByTypeQueryKey({
    path: { collection_id: '__static_value__' }
});

/**
 * Total and filtered annotation counts per annotation type, for the sidebar's
 * "Annotation Types" filter group.
 */
export const useImageAnnotationTypeCounts = (
    getParams: () => {
        collectionId: string;
        filter?: ImageFilter;
        /** Set to false to prevent the query from fetching. Default: true. */
        enabled?: boolean;
    }
) => {
    return createQuery(() => {
        const { collectionId, filter, enabled } = getParams();

        const requestOptions = {
            path: { collection_id: collectionId },
            ...(filter ? { body: { filter } } : {})
        };

        return {
            ...countImageAnnotationsByTypeOptions(requestOptions),
            queryKey: useImageAnnotationTypeCountsQueryKey,
            queryFn: async ({ signal }: { signal: AbortSignal }) => {
                const { data } = await countImageAnnotationsByType({
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
