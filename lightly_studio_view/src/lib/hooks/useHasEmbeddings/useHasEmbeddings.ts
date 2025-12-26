import { hasEmbeddingsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';

export const useHasEmbeddings = ({
    collectionId
}: {
    collectionId: string;
}): CreateQueryResult<boolean, Error> => {
    return createQuery(
        hasEmbeddingsOptions({
            path: { collection_id: collectionId }
        })
    );
};
