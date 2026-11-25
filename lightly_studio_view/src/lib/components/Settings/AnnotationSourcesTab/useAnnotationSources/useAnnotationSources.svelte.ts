import { readAnnotationCollectionsWithCountsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

interface UseAnnotationSourcesParams {
    /** Any collection of the dataset. */
    collectionId: string;
}

// Lists every annotation source of the dataset with its annotation count and the collection it
// belongs to. Deleting goes through the DeleteAnnotationSourceDialog.
export const useAnnotationSources = (getParams: () => UseAnnotationSourcesParams) => {
    const query = createQuery(() => ({
        ...readAnnotationCollectionsWithCountsOptions({
            path: { collection_id: getParams().collectionId }
        }),
        enabled: !!getParams().collectionId
    }));

    return { query };
};
