import {
    getEvaluationRunsQueryKey,
    getEvaluationSampleMetricsInfoQueryKey,
    recomputeEvaluationRunMutation
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';

interface UseRecomputeEvaluationRunParams {
    /** The dataset the evaluation run belongs to. */
    datasetId: string;
    /** The evaluation run to recompute. */
    runId: string;
}

export const useRecomputeEvaluationRun = (getParams: () => UseRecomputeEvaluationRunParams) => {
    const mutation = createMutation(() => recomputeEvaluationRunMutation());
    const client = useQueryClient();

    const recompute = () => {
        const { datasetId, runId } = getParams();
        mutation.mutate(
            { path: { dataset_id: datasetId, run_id: runId } },
            {
                onSuccess: () => {
                    toast.success('Evaluation recomputed');
                    const path = { dataset_id: datasetId };
                    client.invalidateQueries({
                        queryKey: getEvaluationRunsQueryKey({ path })
                    });
                    client.invalidateQueries({
                        queryKey: getEvaluationSampleMetricsInfoQueryKey({ path })
                    });
                    client.invalidateQueries({
                        queryKey: ['getEvaluationConfusionMatrix', datasetId, runId]
                    });
                },
                onError: (error) => {
                    const message =
                        (error as { error?: string })?.error ?? 'Failed to recompute evaluation';
                    toast.error(message);
                }
            }
        );
    };

    return { mutation, recompute };
};
