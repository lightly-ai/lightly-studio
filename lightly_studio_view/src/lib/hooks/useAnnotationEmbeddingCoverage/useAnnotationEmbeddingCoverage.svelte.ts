import { readAnnotationEmbeddingCoverageOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { AnnotationsFilter } from '$lib/api/lightly_studio_local';
import { createQuery } from '@tanstack/svelte-query';

/**
 * Counts the annotations matching a filter, and those of them with an embedding.
 */
export const useAnnotationEmbeddingCoverage = (
    getParams: () => { collectionId: string; filter: AnnotationsFilter | undefined }
) => {
    return createQuery(() => {
        const { collectionId, filter } = getParams();
        return readAnnotationEmbeddingCoverageOptions({
            path: { collection_id: collectionId },
            body: { filters: filter ?? { filter_type: 'annotations' } }
        });
    });
};
