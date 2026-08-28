import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import {
    getEvaluationRunsQueryKey,
    getEvaluationSampleMetricsInfoQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { toast } from 'svelte-sonner';
import { useRecomputeEvaluationRun } from './useRecomputeEvaluationRun.svelte';

vi.mock('@tanstack/svelte-query', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@tanstack/svelte-query')>();
    return { ...actual, createMutation: vi.fn(), useQueryClient: vi.fn() };
});

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

    it('invalidates evaluation runs, sample metrics, and confusion matrix queries on success', () => {
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
            queryKey: getEvaluationRunsQueryKey({ path: { dataset_id: 'dataset-1' } })
        });
        expect(invalidateQueries).toHaveBeenCalledWith({
            queryKey: getEvaluationSampleMetricsInfoQueryKey({ path: { dataset_id: 'dataset-1' } })
        });
        expect(invalidateQueries).toHaveBeenCalledWith({
            queryKey: ['getEvaluationConfusionMatrix', 'dataset-1', 'run-1']
        });
        expect(toast.success).toHaveBeenCalledWith('Evaluation recomputed');
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
