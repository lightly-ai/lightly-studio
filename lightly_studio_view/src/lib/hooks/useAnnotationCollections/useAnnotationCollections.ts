import { readAnnotationCollectionsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { AnnotationCollectionView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';

export const useAnnotationCollections = (
    getParams: () => { collectionId: string }
): CreateQueryResult<AnnotationCollectionView[], Error> => {
    return createQuery(() =>
        readAnnotationCollectionsOptions({
            path: { collection_id: getParams().collectionId }
        })
    );
};
