import { getEvaluationSampleCountsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

export const useEvaluationSampleCounts = ({
    datasetId,
    evaluationId
}: {
    datasetId?: string;
    evaluationId?: string | null;
}) => {
    const options = getEvaluationSampleCountsOptions({
        path: { dataset_id: datasetId ?? '', evaluation_id: evaluationId ?? '' }
    });

    return createQuery({
        ...options,
        enabled: Boolean(datasetId) && Boolean(evaluationId)
    });
};
