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

    beforeEach(() => {
        vi.clearAllMocks();
        useInvalidateAnnotationGridQueries.mockReturnValue(invalidateAnnotationGridQueries);
        vi.mocked(useQueryClient).mockReturnValue({
            invalidateQueries
        } as unknown as ReturnType<typeof useQueryClient>);
    });

    it('invalidates annotation-bearing grids and evaluation runs after a successful delete', async () => {
        vi.mocked(createMutation).mockReturnValue({
            mutate: (_vars: unknown, opts: { onSuccess: () => void }) => {
                opts.onSuccess();
            }
        } as unknown as ReturnType<typeof createMutation>);

        const { deleteAnnotation } = useDeleteAnnotation({ getCollectionId: () => 'col-1' });
        await deleteAnnotation('ann-1', 'classification');

        expect(useInvalidateAnnotationGridQueries).toHaveBeenCalledWith();
        expect(invalidateAnnotationGridQueries).toHaveBeenCalledWith('col-1');
        expect(invalidateQueries).toHaveBeenCalledWith({
            queryKey: [{ _id: 'getEvaluationRuns' }]
        });
    });

    it('fires annotation_deleted with collection_id and annotation_type on success', async () => {
        vi.mocked(createMutation).mockReturnValue({
            mutate: (_vars: unknown, opts: { onSuccess: () => void }) => {
                opts.onSuccess();
            }
        } as unknown as ReturnType<typeof createMutation>);

        const { deleteAnnotation } = useDeleteAnnotation({ getCollectionId: () => 'col-1' });
        await deleteAnnotation('ann-1', 'classification');

        expect(trackEvent).toHaveBeenCalledWith('annotation_deleted', {
            collection_id: 'col-1',
            annotation_type: 'classification'
        });
    });

    it('includes the provided annotation_type in the event', async () => {
        vi.mocked(createMutation).mockReturnValue({
            mutate: (_vars: unknown, opts: { onSuccess: () => void }) => {
                opts.onSuccess();
            }
        } as unknown as ReturnType<typeof createMutation>);

        const { deleteAnnotation } = useDeleteAnnotation({ getCollectionId: () => 'col-1' });
        await deleteAnnotation('ann-1', 'object_detection');

        expect(trackEvent).toHaveBeenCalledWith('annotation_deleted', {
            collection_id: 'col-1',
            annotation_type: 'object_detection'
        });
    });
});
