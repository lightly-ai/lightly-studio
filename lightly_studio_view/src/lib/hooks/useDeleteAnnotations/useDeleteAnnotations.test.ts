import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createMutation } from '@tanstack/svelte-query';
import { useDeleteAnnotations } from './useDeleteAnnotations.svelte';

vi.mock('@tanstack/svelte-query', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@tanstack/svelte-query')>();
    return { ...actual, createMutation: vi.fn() };
});

const trackEvent = vi.fn();
vi.mock('$lib/hooks/usePostHog', () => ({
    usePostHog: () => ({ trackEvent })
}));

const invalidateAnnotationDeleteQueries = vi.fn();
vi.mock(
    '$lib/hooks/useInvalidateAnnotationDeleteQueries/useInvalidateAnnotationDeleteQueries',
    () => ({
        useInvalidateAnnotationDeleteQueries: () => invalidateAnnotationDeleteQueries
    })
);

describe('useDeleteAnnotations', () => {
    const mutateAsync = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(createMutation).mockReturnValue({
            mutateAsync
        } as unknown as ReturnType<typeof createMutation>);
    });

    it('deletes the annotations, refreshes queries and tracks the event', async () => {
        mutateAsync.mockResolvedValue({ deleted_count: 2 });

        const { deleteAnnotations } = useDeleteAnnotations({ getCollectionId: () => 'col-1' });
        const deletedCount = await deleteAnnotations(['ann-1', 'ann-2']);

        expect(deletedCount).toBe(2);
        expect(mutateAsync).toHaveBeenCalledWith({
            path: { collection_id: 'col-1' },
            body: { annotation_ids: ['ann-1', 'ann-2'] }
        });
        expect(invalidateAnnotationDeleteQueries).toHaveBeenCalledWith('col-1');
        expect(trackEvent).toHaveBeenCalledWith('annotations_deleted', {
            collection_id: 'col-1',
            count: 2
        });
    });

    it('rejects and does not refresh queries when the request fails', async () => {
        mutateAsync.mockRejectedValue(new Error('Request failed'));

        const { deleteAnnotations } = useDeleteAnnotations({ getCollectionId: () => 'col-1' });

        await expect(deleteAnnotations(['ann-1'])).rejects.toThrow('Request failed');
        expect(invalidateAnnotationDeleteQueries).not.toHaveBeenCalled();
        expect(trackEvent).not.toHaveBeenCalled();
    });
});
