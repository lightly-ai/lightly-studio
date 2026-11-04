import { readAnnotationCollectionsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type {
    AnnotationCollectionView,
    ReadAnnotationCollectionsError
} from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';

export const useAnnotationCollections = (
    getParams: () => { collectionId?: string }
): CreateQueryResult<AnnotationCollectionView[], ReadAnnotationCollectionsError> => {
    return createQuery(() => {
        const { collectionId } = getParams();
        const options = readAnnotationCollectionsOptions({
            path: { collection_id: collectionId ?? '' }
        });
        return {
            ...options,
            enabled: Boolean(collectionId)
        };
    });
};
