import { readAnnotationLabelsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

export const useAnnotationLabels = (
    getParams: () => { collectionId: string; enabled?: boolean }
) => {
    return createQuery(() => {
        const { collectionId, enabled = true } = getParams();
        return {
            ...readAnnotationLabelsOptions({ path: { collection_id: collectionId } }),
            enabled
        };
    });
};
