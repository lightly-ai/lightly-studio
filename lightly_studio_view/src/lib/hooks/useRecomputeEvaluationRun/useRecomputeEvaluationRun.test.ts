import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import {
    getEvaluationRunsQueryKey,
    getEvaluationSampleMetricsInfoQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { updateRun } from '$lib/api/lightly_studio_local';
import { toast } from 'svelte-sonner';
import { ANNOTATIONS_INFINITE_QUERY_KEY_ROOT } from '$lib/hooks/useAnnotationsInfinite';
import { useRecomputeEvaluationRun } from './useRecomputeEvaluationRun.svelte';

vi.mock('@tanstack/svelte-query', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@tanstack/svelte-query')>();
    return { ...actual, createMutation: vi.fn(), useQueryClient: vi.fn() };
});

vi.mock('$lib/api/lightly_studio_local', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/api/lightly_studio_local')>()),
    updateRun: vi.fn().mockResolvedValue({ data: {} })
}));

vi.mock('svelte-sonner', () => ({
    toast: { success: vi.fn(), error: vi.fn() }
}));

describe('useRecomputeEvaluationRun', () => {
    const invalidateQueries = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(useQueryClient).mockReturnValue({
            invalidateQueries
        } as unknown as ReturnType<typeof useQueryClient>);
    });

    it('saves changed parameters through the update endpoint', async () => {
        const config = { iou_threshold: 0.75, classwise: false };
        useRecomputeEvaluationRun(() => ({ datasetId: 'dataset-1', runId: 'run-1', config }));
        const options = vi.mocked(createMutation).mock.calls[0][0]();
        const path = { dataset_id: 'dataset-1', run_id: 'run-1' };
        await options.mutationFn!(
            { path },
            { client: useQueryClient(), meta: undefined, mutationKey: undefined }
        );
        expect(updateRun).toHaveBeenCalledWith({ path, body: { config }, throwOnError: true });
    });

    it('invalidates evaluation runs, sample metrics, and confusion matrix queries on success', () => {
        vi.mocked(createMutation).mockReturnValue({
            mutate: (_vars: unknown, opts: { onSuccess: () => void }) => {
                opts.onSuccess();
            }
        } as unknown as ReturnType<typeof createMutation>);

        const onSuccess = vi.fn();
        const { recompute } = useRecomputeEvaluationRun(() => ({
            datasetId: 'dataset-1',
            runId: 'run-1',
            onSuccess
        }));
        recompute();

        expect(invalidateQueries).toHaveBeenCalledWith({
            queryKey: getEvaluationRunsQueryKey({ path: { dataset_id: 'dataset-1' } })
        });
        expect(invalidateQueries).toHaveBeenCalledWith({
            queryKey: getEvaluationSampleMetricsInfoQueryKey({ path: { dataset_id: 'dataset-1' } })
        });
        expect(invalidateQueries).toHaveBeenCalledWith({
            queryKey: ['getEvaluationConfusionMatrix', 'dataset-1', 'run-1']
        });
        expect(toast.success).toHaveBeenCalledWith('Evaluation recomputed');
        expect(onSuccess).toHaveBeenCalledOnce();
    });

    it('invalidates the annotation grid list query on success, so the sort order refreshes', () => {
        vi.mocked(createMutation).mockReturnValue({
            mutate: (_vars: unknown, opts: { onSuccess: () => void }) => {
                opts.onSuccess();
            }
        } as unknown as ReturnType<typeof createMutation>);

        const { recompute } = useRecomputeEvaluationRun(() => ({
            datasetId: 'dataset-1',
            runId: 'run-1'
        }));
        recompute();

        expect(invalidateQueries).toHaveBeenCalledWith({
            queryKey: [ANNOTATIONS_INFINITE_QUERY_KEY_ROOT]
        });
    });

    it('shows the server error message on failure', () => {
        vi.mocked(createMutation).mockReturnValue({
            mutate: (_vars: unknown, opts: { onError: (error: unknown) => void }) => {
                opts.onError({ error: 'Run not found' });
            }
        } as unknown as ReturnType<typeof createMutation>);

        const { recompute } = useRecomputeEvaluationRun(() => ({
            datasetId: 'dataset-1',
            runId: 'run-1'
        }));
        recompute();

        expect(toast.error).toHaveBeenCalledWith('Run not found');
    });

    it('shows a fallback error message when the server provides none', () => {
        vi.mocked(createMutation).mockReturnValue({
            mutate: (_vars: unknown, opts: { onError: (error: unknown) => void }) => {
                opts.onError({});
            }
        } as unknown as ReturnType<typeof createMutation>);

        const { recompute } = useRecomputeEvaluationRun(() => ({
            datasetId: 'dataset-1',
            runId: 'run-1'
        }));
        recompute();

        expect(toast.error).toHaveBeenCalledWith('Failed to recompute evaluation');
    });
});
