import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import {
    deleteRunMutation,
    getEvaluationRunsQueryKey,
    getEvaluationSampleMetricsInfoQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useAnnotationSortBy } from '$lib/hooks/useAnnotationSortBy/useAnnotationSortBy';
import { ANNOTATIONS_INFINITE_QUERY_KEY_ROOT } from '$lib/hooks/useAnnotationsInfinite';
import { get } from 'svelte/store';
import { toast } from 'svelte-sonner';

interface Params {
    datasetId: string;
    run: { id: string; name: string };
    onSuccess: () => void;
}

export const useDeleteEvaluationRun = (getParams: () => Params) => {
    const client = useQueryClient();
    const filters = useImageFilters();
    const { clearRun } = useAnnotationSortBy();
    const mutation = createMutation(() => ({ ...deleteRunMutation() }));
    const remove = () => {
        if (mutation.isPending) return;
        const { datasetId, run, onSuccess } = getParams();
        mutation.mutate(
            { path: { dataset_id: datasetId, run_id: run.id } },
            {
                onSuccess: () => {
                    const sort = get(filters.imageSortBy);
                    const remaining = sort?.filter(
                        (expr) =>
                            expr.source !== 'evaluation_metric' ||
                            expr.evaluation_run_name !== run.name
                    );
                    if (remaining?.length !== sort?.length) {
                        filters.updateSortBy(remaining?.length ? remaining : null);
                    }
                    if (
                        get(filters.imageFilter)?.sample_filter?.confusion_cell
                            ?.evaluation_run_id === run.id
                    ) {
                        filters.updateConfusionCell(null);
                    }
                    clearRun(run.id);
                    const path = { dataset_id: datasetId };
                    // Annotation metrics are cached by source rather than dataset.
                    for (const queryKey of [
                        getEvaluationRunsQueryKey({ path }),
                        getEvaluationSampleMetricsInfoQueryKey({ path }),
                        [{ _id: 'getEvaluationAnnotationMetricsInfo' }],
                        ['readImagesInfinite'],
                        [ANNOTATIONS_INFINITE_QUERY_KEY_ROOT]
                    ]) {
                        client.invalidateQueries({ queryKey });
                    }
                    toast.success('Evaluation deleted');
                    onSuccess();
                },
                onError: () => toast.error('Failed to delete evaluation. Try again.')
            }
        );
    };
    return { mutation, remove };
};
