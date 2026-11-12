import { hasEmbeddingsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { HasEmbeddingsError } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';

export const useHasEmbeddings = (
    getParams: () => { collectionId: string }
): CreateQueryResult<boolean, HasEmbeddingsError> => {
    return createQuery(() =>
        hasEmbeddingsOptions({
            path: { collection_id: getParams().collectionId }
        })
    );
};
