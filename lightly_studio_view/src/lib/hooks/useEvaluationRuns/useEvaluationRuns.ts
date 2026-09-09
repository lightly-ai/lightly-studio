import { getEvaluationRunsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery, useQueryClient } from '@tanstack/svelte-query';

export const useEvaluationRuns = (getParams: () => { datasetId: string }) => {
    return createQuery(() =>
        getEvaluationRunsOptions({
            path: { dataset_id: getParams().datasetId }
        })
    );
};

/** Invalidates all cached evaluation-run lists regardless of dataset.
 *  Call after any annotation mutation that may have marked a run as stale. */
export const useInvalidateEvaluationRunsQueries = () => {
    const client = useQueryClient();
    return () => {
        // Partial match on the _id field set by the @hey-api generated createQueryKey helper.
        // This invalidates getEvaluationRuns queries for every dataset.
        client.invalidateQueries({
            queryKey: [{ _id: 'getEvaluationRuns' }]
        });
    };
};
