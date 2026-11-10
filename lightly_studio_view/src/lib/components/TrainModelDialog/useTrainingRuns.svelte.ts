import {
    cancelTrainingRunByIdMutation,
    createTrainingRunMutation,
    getTrainingRunsOptions,
    getTrainingRunsQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { CreateTrainingRunData } from '$lib/api/lightly_studio_local/types.gen';
import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';
import { isActiveRun } from './TrainModelDialog.helpers';

const POLL_INTERVAL_MS = 2000;

type TrainingRunRequest = CreateTrainingRunData['body'];

interface UseTrainingRunsParams {
    collectionId: string;
}

/**
 * Query and mutations for the training runs of a collection.
 *
 * The query polls while a run is active. When a run stops being active, the evaluation
 * runs and the annotation sources are refreshed, so the new results show without a reload.
 */
export const useTrainingRuns = (getParams: () => UseTrainingRunsParams) => {
    const client = useQueryClient();
    const path = () => ({ collection_id: getParams().collectionId });

    const query = createQuery(() => ({
        ...getTrainingRunsOptions({ path: path() }),
        refetchInterval: (q) => ((q.state.data ?? []).some(isActiveRun) ? POLL_INTERVAL_MS : false)
    }));
    const startMutation = createMutation(() => createTrainingRunMutation());
    const cancelMutation = createMutation(() => cancelTrainingRunByIdMutation());

    let wasActive = false;
    $effect(() => {
        const isActive = (query.data ?? []).some(isActiveRun);
        if (wasActive && !isActive) {
            client.invalidateQueries({ queryKey: [{ _id: 'getEvaluationRuns' }] });
            client.invalidateQueries({ queryKey: [{ _id: 'readAnnotationCollections' }] });
        }
        wasActive = isActive;
    });

    const refreshRuns = () =>
        client.invalidateQueries({ queryKey: getTrainingRunsQueryKey({ path: path() }) });

    const showError = (error: unknown, fallback: string) =>
        toast.error((error as { error?: string })?.error ?? fallback);

    const start = (body: TrainingRunRequest) =>
        startMutation.mutate(
            { path: path(), body },
            {
                onSuccess: () => {
                    toast.success('Training started');
                    refreshRuns();
                },
                onError: (error) => showError(error, 'Failed to start training')
            }
        );

    const cancel = (trainingRunId: string) =>
        cancelMutation.mutate(
            { path: { ...path(), training_run_id: trainingRunId } },
            {
                onSuccess: refreshRuns,
                onError: (error) => showError(error, 'Failed to cancel training')
            }
        );

    return { query, startMutation, cancelMutation, start, cancel };
};
