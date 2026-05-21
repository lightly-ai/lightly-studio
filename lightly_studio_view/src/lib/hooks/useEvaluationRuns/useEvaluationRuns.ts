import { getEvaluationRunsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

export const useEvaluationRuns = (getParams: () => { datasetId: string }) => {
    return createQuery(() =>
        getEvaluationRunsOptions({
            path: { dataset_id: getParams().datasetId }
        })
    );
};
