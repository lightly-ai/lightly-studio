import { getEvaluationSampleMetricsInfoOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { EvaluationRunMetricsInfoView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';

interface UseEvaluationSampleMetricsInfoParams {
    datasetId: string;
}

export const useEvaluationSampleMetricsInfo = ({
    datasetId
}: UseEvaluationSampleMetricsInfoParams): CreateQueryResult<
    EvaluationRunMetricsInfoView[],
    Error
> => {
    console.log(datasetId);
    return createQuery(
        getEvaluationSampleMetricsInfoOptions({
            path: { dataset_id: datasetId }
        })
    );
};
