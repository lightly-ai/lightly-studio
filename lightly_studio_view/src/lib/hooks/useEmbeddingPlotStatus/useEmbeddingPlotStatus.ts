import {
    get2dEmbeddingsStatusOptions,
    get2dEmbeddingsStatusQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery, useQueryClient } from '@tanstack/svelte-query';

export function useEmbeddingPlotStatus(getCollectionId: () => string) {
    return createQuery(() =>
        get2dEmbeddingsStatusOptions({ path: { collection_id: getCollectionId() } })
    );
}

// A compute can end after the panel moved to another collection, so the caller names the collection.
export function useRefetchEmbeddingPlotStatus() {
    const queryClient = useQueryClient();
    return (collectionId: string) =>
        queryClient.refetchQueries({
            queryKey: get2dEmbeddingsStatusQueryKey({ path: { collection_id: collectionId } })
        });
}
