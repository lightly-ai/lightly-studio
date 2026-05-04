import { listEvaluationsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

export const useEvaluations = ({ datasetId }: { datasetId?: string }) => {
    const options = listEvaluationsOptions({
        path: { dataset_id: datasetId ?? '' }
    });

    return createQuery({
        ...options,
        enabled: Boolean(datasetId)
    });
};
