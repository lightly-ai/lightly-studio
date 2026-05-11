import { readAnnotationCollectionsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

export const useAnnotationCollections = ({ collectionId }: { collectionId: string }) => {
    return createQuery(
        readAnnotationCollectionsOptions({
            path: { collection_id: collectionId }
        })
    );
};
