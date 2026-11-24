import type { Embeddings2dStatus } from '$lib/api/lightly_studio_local';
import {
    get2dEmbeddingsStatusOptions,
    get2dEmbeddingsStatusQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery, useQueryClient, type CreateQueryResult } from '@tanstack/svelte-query';

export function useEmbeddingPlotStatus(
    getCollectionId: () => string
): CreateQueryResult<Embeddings2dStatus, Error> {
    return createQuery(() =>
        get2dEmbeddingsStatusOptions({ path: { collection_id: getCollectionId() } })
    );
}

// A compute can end after the panel moved to another collection, so the caller names the collection.
export function useRefetchEmbeddingPlotStatus(): (collectionId: string) => Promise<void> {
    const queryClient = useQueryClient();
    return (collectionId: string) =>
        queryClient.refetchQueries({
            queryKey: get2dEmbeddingsStatusQueryKey({ path: { collection_id: collectionId } })
        });
}
