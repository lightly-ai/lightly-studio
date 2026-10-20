import { beforeEach, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useAnnotationSortBy } from '$lib/hooks/useAnnotationSortBy/useAnnotationSortBy';
import { toast } from 'svelte-sonner';
import { useDeleteEvaluationRun } from './useDeleteEvaluationRun.svelte';

vi.mock('@tanstack/svelte-query', async (original) => ({
    ...(await original<typeof import('@tanstack/svelte-query')>()),
    useQueryClient: () => ({ invalidateQueries }),
    createMutation: () => ({
        mutate: (_vars: unknown, callbacks: { onSuccess: () => void; onError: () => void }) => {
            succeed = callbacks.onSuccess;
            fail = callbacks.onError;
        }
    })
}));
vi.mock('svelte-sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
const invalidateQueries = vi.fn();
const onSuccess = vi.fn();
const filters = useImageFilters();
const annotations = useAnnotationSortBy();
let succeed: () => void;
let fail: () => void;
const ordinarySort = {
    source: 'image' as const,
    field_name: 'file_path_abs',
    direction: 'asc' as const
};

beforeEach(() => {
    vi.clearAllMocks();
    filters.updateFilterParams({
        collection_id: 'images',
        mode: 'normal',
        filters: { tag_ids: ['tag'], sample_ids: ['sample'] }
    });
    filters.updateSortBy(null);
    annotations.setSortBy('source', null);
});

it.each(['run-1', 'other-run'])(
    'clears only selections for the deleted evaluation (%s)',
    (selectedRun) => {
        const name = selectedRun === 'run-1' ? 'Evaluation' : 'Other';
        const sort = [
            {
                source: 'evaluation_metric' as const,
                evaluation_run_name: name,
                metric_name: 'fp',
                direction: 'desc' as const
            },
            ordinarySort
        ];
        filters.updateSortBy(sort);
        const cell = { evaluation_run_id: selectedRun, gt_label: 'cat', pred_label: 'dog' };
        filters.updateConfusionCell(cell);
        const annotationSort = {
            source: 'annotation_evaluation_metric' as const,
            evaluation_run_id: selectedRun,
            metric_name: 'iou',
            direction: 'asc' as const
        };
        annotations.setSortBy('source', annotationSort);
        const { remove } = useDeleteEvaluationRun(() => ({
            datasetId: 'dataset',
            run: { id: 'run-1', name: 'Evaluation' },
            onSuccess
        }));
        remove();
        expect(get(filters.imageSortBy)).toEqual(sort);
        fail();
        expect(get(filters.imageFilter)?.sample_filter?.confusion_cell).toEqual(cell);
        expect(annotations.getSortBy('source')).toEqual(annotationSort);
        expect(onSuccess).not.toHaveBeenCalled();
        expect(invalidateQueries).not.toHaveBeenCalled();
        expect(toast.error).toHaveBeenCalled();
        succeed();
        expect(get(filters.imageSortBy)).toEqual(selectedRun === 'run-1' ? [ordinarySort] : sort);
        expect(get(filters.imageFilter)?.sample_filter).toEqual({
            tag_ids: ['tag'],
            sample_ids: ['sample'],
            confusion_cell: selectedRun === 'run-1' ? undefined : cell
        });
        expect(annotations.getSortBy('source')).toEqual(
            selectedRun === 'run-1' ? null : annotationSort
        );
        expect(invalidateQueries).toHaveBeenCalledWith({
            queryKey: [{ _id: 'getEvaluationAnnotationMetricsInfo' }]
        });
        expect(onSuccess).toHaveBeenCalledOnce();
    }
);
