import { hasEmbeddingsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

export const useHasEmbeddings = ({ collectionId }: { collectionId: string }) => {
    return createQuery(
        hasEmbeddingsOptions({
            path: { collection_id: collectionId }
        })
    );
};
