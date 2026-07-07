import { getEvaluationConfusionMatrix } from '$lib/api/lightly_studio_local/sdk.gen';
import { createQuery } from '@tanstack/svelte-query';

interface Params {
    datasetId: string;
    evaluationRunId: string;
    /** Set to false to skip fetching (e.g. while the run item is collapsed). */
    enabled?: boolean;
}

/**
 * Fetches the confusion matrix for a given evaluation run.
 */
export const useEvaluationConfusionMatrix = (getParams: () => Params) => {
    return createQuery(() => {
        const { datasetId, evaluationRunId, enabled = true } = getParams();
        return {
            enabled,
            queryKey: ['getEvaluationConfusionMatrix', datasetId, evaluationRunId],
            queryFn: async () => {
                try {
                    const { data } = await getEvaluationConfusionMatrix({
                        path: { dataset_id: datasetId, evaluation_run_id: evaluationRunId },
                        throwOnError: true
                    });
                    return data ?? null;
                } catch (error) {
                    if ((error as { status?: number })?.status === 501) {
                        return null;
                    }
                    throw error;
                }
            }
        };
    });
};
