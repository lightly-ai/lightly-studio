import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { useDeleteAnnotation } from './useDeleteAnnotation';

vi.mock('@tanstack/svelte-query', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@tanstack/svelte-query')>();
    return { ...actual, createMutation: vi.fn(), useQueryClient: vi.fn() };
});

const trackEvent = vi.fn();
vi.mock('$lib/hooks/usePostHog', () => ({
    usePostHog: () => ({ trackEvent })
}));

const { invalidateAnnotationGridQueries, useInvalidateAnnotationGridQueries } = vi.hoisted(() => ({
    invalidateAnnotationGridQueries: vi.fn(),
    useInvalidateAnnotationGridQueries: vi.fn()
}));
vi.mock('$lib/hooks/useInvalidateAnnotationGridQueries', () => ({
    useInvalidateAnnotationGridQueries
}));

describe('useDeleteAnnotation', () => {
    const invalidateQueries = vi.fn();
    const mockMutateAsync = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        mockMutateAsync.mockResolvedValue(undefined);
        vi.mocked(createMutation).mockReturnValue({
            mutateAsync: mockMutateAsync
        } as unknown as ReturnType<typeof createMutation>);
        useInvalidateAnnotationGridQueries.mockReturnValue(invalidateAnnotationGridQueries);
        vi.mocked(useQueryClient).mockReturnValue({
            invalidateQueries
        } as unknown as ReturnType<typeof useQueryClient>);
    });

    it('invalidates annotation-bearing grids and evaluation runs after a successful delete', async () => {
        const { deleteAnnotation } = useDeleteAnnotation({ getCollectionId: () => 'col-1' });
        await deleteAnnotation('ann-1', 'classification');

        expect(useInvalidateAnnotationGridQueries).toHaveBeenCalledWith();
        expect(invalidateAnnotationGridQueries).toHaveBeenCalledWith('col-1');
        expect(invalidateQueries).toHaveBeenCalledWith({
            queryKey: [{ _id: 'getEvaluationRuns' }]
        });
    });

    it('fires annotation_deleted with collection_id and annotation_type on success', async () => {
        const { deleteAnnotation } = useDeleteAnnotation({ getCollectionId: () => 'col-1' });
        await deleteAnnotation('ann-1', 'classification');

        expect(trackEvent).toHaveBeenCalledWith('annotation_deleted', {
            collection_id: 'col-1',
            annotation_type: 'classification'
        });
    });

    it('uses an explicit collection after navigation and includes the annotation type', async () => {
        const { deleteAnnotation } = useDeleteAnnotation({ getCollectionId: () => 'new-col' });
        await deleteAnnotation('ann-1', 'object_detection', 'col-1');

        expect(trackEvent).toHaveBeenCalledWith('annotation_deleted', {
            collection_id: 'col-1',
            annotation_type: 'object_detection'
        });
    });

    it('calls mutateAsync with only the variables and runs refetch and tracking once', async () => {
        const { deleteAnnotation } = useDeleteAnnotation({ getCollectionId: () => 'col-1' });
        await deleteAnnotation('ann-1', 'classification');

        expect(mockMutateAsync).toHaveBeenCalledTimes(1);
        expect(mockMutateAsync.mock.calls[0]).toEqual([
            { path: { collection_id: 'col-1', annotation_id: 'ann-1' } }
        ]);
        expect(invalidateAnnotationGridQueries).toHaveBeenCalledTimes(1);
        expect(trackEvent).toHaveBeenCalledTimes(1);
    });

    it('rejects with the same error and does not refetch when mutateAsync rejects', async () => {
        const error = new Error('boom');
        mockMutateAsync.mockRejectedValue(error);

        const { deleteAnnotation } = useDeleteAnnotation({ getCollectionId: () => 'col-1' });

        await expect(deleteAnnotation('ann-1', 'classification')).rejects.toBe(error);
        expect(invalidateAnnotationGridQueries).not.toHaveBeenCalled();
        expect(invalidateQueries).not.toHaveBeenCalled();
        expect(trackEvent).not.toHaveBeenCalled();
    });
});
