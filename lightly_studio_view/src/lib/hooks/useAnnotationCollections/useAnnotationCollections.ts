import { listAnnotationCollectionsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

export const useAnnotationCollections = ({ datasetId }: { datasetId?: string }) => {
    const options = listAnnotationCollectionsOptions({
        path: { dataset_id: datasetId ?? '' }
    });

    return createQuery({
        ...options,
        enabled: Boolean(datasetId)
    });
};
