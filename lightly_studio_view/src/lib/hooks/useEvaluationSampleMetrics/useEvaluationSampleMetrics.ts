import { getEvaluationSampleMetricsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

export const useEvaluationSampleMetrics = ({
    datasetId,
    evaluationId,
    labelId
}: {
    datasetId?: string;
    evaluationId?: string | null;
    labelId?: string;
}) => {
    const options = getEvaluationSampleMetricsOptions({
        path: { dataset_id: datasetId ?? '', evaluation_id: evaluationId ?? '' },
        query: labelId ? { label_id: labelId } : {}
    });

    return createQuery({
        ...options,
        enabled: Boolean(datasetId) && Boolean(evaluationId)
    });
};
