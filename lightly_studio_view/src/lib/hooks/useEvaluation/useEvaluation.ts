import { getEvaluationOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

export const useEvaluation = ({
    datasetId,
    evaluationId
}: {
    datasetId?: string;
    evaluationId?: string;
}) => {
    const options = getEvaluationOptions({
        path: {
            dataset_id: datasetId ?? '',
            evaluation_id: evaluationId ?? ''
        }
    });

    return createQuery({
        ...options,
        enabled: Boolean(datasetId && evaluationId)
    });
};
