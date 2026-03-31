import { createQuery } from '@tanstack/svelte-query';
import type { ImageFilter } from '$lib/api/lightly_studio_local';
import {
    countImageAnnotationsByCollectionOptions,
    countImageAnnotationsByCollectionQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { countImageAnnotationsByCollection } from '$lib/api/lightly_studio_local/sdk.gen';

export const useImageAnnotationCountsQueryKey = countImageAnnotationsByCollectionQueryKey({
    path: { collection_id: '__static_value__' }
});

export const useImageAnnotationCounts = ({
    collectionId,
    filter
}: {
    collectionId: string;
    filter?: ImageFilter;
}) => {
    const requestOptions = {
        path: { collection_id: collectionId },
        ...(filter ? { body: { filter } } : {})
    } as const;

    const options = countImageAnnotationsByCollectionOptions(requestOptions);
    const queryKey = useImageAnnotationCountsQueryKey;

    return createQuery({
        ...options,
        queryKey,
        queryFn: async ({ signal }) => {
            const { data } = await countImageAnnotationsByCollection({
                ...requestOptions,
                signal,
                throwOnError: true
            });
            return data;
        }
    });
};
