import { getEvaluationRunsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { EvaluationRunView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';

interface UseEvaluationRunsParams {
    datasetId: string;
}

export const useEvaluationRuns = ({
    datasetId
}: UseEvaluationRunsParams): CreateQueryResult<EvaluationRunView[], Error> => {
    return createQuery(() =>
        getEvaluationRunsOptions({
            path: { dataset_id: datasetId }
        })
    );
};
