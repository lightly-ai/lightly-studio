import {
    createEvaluationRunMutation,
    getEvaluationRunsQueryKey,
    getEvaluationSampleMetricsInfoQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { CreateEvaluationRunData } from '$lib/api/lightly_studio_local/types.gen';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';

type EvaluationRunRequest = CreateEvaluationRunData['body'];

interface UseTriggerEvaluationParams {
    datasetId: string;
}

/**
 * Mutation hook to trigger a new evaluation run.
 *
 * On success it shows a toast and invalidates the dataset's evaluation runs
 * query so the new run appears in the panel.
 */
export const useTriggerEvaluation = (getParams: () => UseTriggerEvaluationParams) => {
    const mutation = createMutation(() => createEvaluationRunMutation());
    const client = useQueryClient();

    const trigger = (body: EvaluationRunRequest): Promise<boolean> =>
        new Promise((resolve) => {
            const { datasetId } = getParams();
            mutation.mutate(
                { path: { dataset_id: datasetId }, body },
                {
                    onSuccess: () => {
                        toast.success('Evaluation started');
                        const path = { dataset_id: datasetId };
                        // Refresh the runs list and the per-run metric bounds that
                        // feed the sort options, so both update without a reload.
                        client.invalidateQueries({
                            queryKey: getEvaluationRunsQueryKey({ path })
                        });
                        client.invalidateQueries({
                            queryKey: getEvaluationSampleMetricsInfoQueryKey({ path })
                        });
                        resolve(true);
                    },
                    onError: (error) => {
                        const message =
                            (error as { error?: string })?.error ?? 'Failed to start evaluation';
                        toast.error(message);
                        resolve(false);
                    }
                }
            );
        });

    return { mutation, trigger };
};
