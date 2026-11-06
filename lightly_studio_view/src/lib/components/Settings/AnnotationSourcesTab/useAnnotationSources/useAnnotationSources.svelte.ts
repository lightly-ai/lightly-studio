import { readAnnotationCollectionsWithCountsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

interface UseAnnotationSourcesParams {
    /** The collection that owns the annotation sources. */
    collectionId: string;
}

// Lists the annotation sources of a collection with their annotation counts. Deleting goes
// through the DeleteAnnotationSourceDialog.
export const useAnnotationSources = (getParams: () => UseAnnotationSourcesParams) => {
    const query = createQuery(() => ({
        ...readAnnotationCollectionsWithCountsOptions({
            path: { collection_id: getParams().collectionId }
        }),
        enabled: !!getParams().collectionId
    }));

    return { query };
};
