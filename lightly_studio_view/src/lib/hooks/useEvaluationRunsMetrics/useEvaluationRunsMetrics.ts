import { getEvaluationRunsMetricsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

interface UseEvaluationRunsMetricsParams {
    datasetId: string;
    /** Runs to compare. The response keeps this order. */
    runIds: string[];
    /** Tags to compare the runs on. Each run gets one slice for each tag. */
    tagIds: string[];
    enabled?: boolean;
}

/** Fetches the aggregate metrics of several evaluation runs, for comparison. */
export const useEvaluationRunsMetrics = (getParams: () => UseEvaluationRunsMetricsParams) =>
    createQuery(() => {
        const { datasetId, runIds, tagIds, enabled = true } = getParams();
        return {
            ...getEvaluationRunsMetricsOptions({
                path: { dataset_id: datasetId },
                query: { run_ids: runIds, tag_ids: tagIds }
            }),
            enabled
        };
    });
