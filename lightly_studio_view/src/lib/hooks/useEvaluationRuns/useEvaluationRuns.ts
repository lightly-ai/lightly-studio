import { createQuery } from '@tanstack/svelte-query';
import { listEvaluationRuns, getConfusionMatrix } from '$lib/api/evaluationRunApi';

export const useEvaluationRuns = (datasetId: string) =>
    createQuery({
        queryKey: ['evaluation_runs', datasetId],
        queryFn: () => listEvaluationRuns(datasetId),
        enabled: !!datasetId
    });

export const useConfusionMatrix = (runId: string | null) =>
    createQuery({
        queryKey: ['confusion_matrix', runId],
        queryFn: () => getConfusionMatrix(runId!),
        enabled: !!runId
    });
