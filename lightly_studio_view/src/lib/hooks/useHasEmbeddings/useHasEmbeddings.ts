import { hasEmbeddingsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { CollectionEmbeddingsStatus } from '$lib/api/lightly_studio_local';
import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';

export const useHasEmbeddings = (
    getParams: () => { collectionId: string }
): CreateQueryResult<CollectionEmbeddingsStatus, Error> => {
    return createQuery(() =>
        hasEmbeddingsOptions({
            path: { collection_id: getParams().collectionId }
        })
    );
};
