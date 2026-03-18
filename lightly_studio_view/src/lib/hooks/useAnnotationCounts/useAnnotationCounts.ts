import { createQuery } from '@tanstack/svelte-query';
import type { ImageFilter } from '$lib/api/lightly_studio_local';
import {
    countAnnotationsByCollectionOptions,
    countAnnotationsByCollectionQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { countAnnotationsByCollection } from '$lib/api/lightly_studio_local/sdk.gen';

export const useAnnotationCountsQueryKey = countAnnotationsByCollectionQueryKey({
    path: { collection_id: '__static_value__' }
});
export const useAnnotationCounts = ({
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

    const options = countAnnotationsByCollectionOptions(requestOptions);
    const queryKey = useAnnotationCountsQueryKey;
    return createQuery({
        ...options,
        queryKey,
        queryFn: async ({ signal }) => {
            const { data } = await countAnnotationsByCollection({
                ...requestOptions,
                signal,
                throwOnError: true
            });
            return data;
        }
    });
};
