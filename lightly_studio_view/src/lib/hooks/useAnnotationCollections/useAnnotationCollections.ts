import { readAnnotationCollectionsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { AnnotationCollectionView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';

interface UseAnnotationCollectionsParams {
    // The ID of the image collection for which to fetch annotation collections.
    imageCollectionId: string;
}

export const useAnnotationCollections = ({
    imageCollectionId
}: UseAnnotationCollectionsParams): CreateQueryResult<AnnotationCollectionView[], Error> => {
    return createQuery(
        readAnnotationCollectionsOptions({
            path: { collection_id: imageCollectionId }
        })
    );
};
