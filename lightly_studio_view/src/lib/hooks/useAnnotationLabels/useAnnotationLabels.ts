import { readAnnotationLabelsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

export const useAnnotationLabels = ({ datasetId }: { datasetId: string }) =>
    createQuery(
        readAnnotationLabelsOptions({
            path: { dataset_id: datasetId }
        })
    );
