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

describe('useDeleteAnnotation', () => {
    const invalidateQueries = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(useQueryClient).mockReturnValue({
            invalidateQueries
        } as unknown as ReturnType<typeof useQueryClient>);
    });

    it('fires annotation_deleted with collection_id on success', async () => {
        vi.mocked(createMutation).mockReturnValue({
            mutate: (_vars: unknown, opts: { onSuccess: () => void }) => {
                opts.onSuccess();
            }
        } as unknown as ReturnType<typeof createMutation>);

        const { deleteAnnotation } = useDeleteAnnotation({ collectionId: 'col-1' });
        await deleteAnnotation('ann-1');

        expect(trackEvent).toHaveBeenCalledWith('annotation_deleted', {
            collection_id: 'col-1'
        });
    });

    it('includes annotation_type when provided', async () => {
        vi.mocked(createMutation).mockReturnValue({
            mutate: (_vars: unknown, opts: { onSuccess: () => void }) => {
                opts.onSuccess();
            }
        } as unknown as ReturnType<typeof createMutation>);

        const { deleteAnnotation } = useDeleteAnnotation({ collectionId: 'col-1' });
        await deleteAnnotation('ann-1', 'object_detection');

        expect(trackEvent).toHaveBeenCalledWith('annotation_deleted', {
            collection_id: 'col-1',
            annotation_type: 'object_detection'
        });
    });
});
