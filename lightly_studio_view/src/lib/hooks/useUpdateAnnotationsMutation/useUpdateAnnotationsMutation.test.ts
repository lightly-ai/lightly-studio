import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { useUpdateAnnotationsMutation } from './useUpdateAnnotationsMutation';

vi.mock('@tanstack/svelte-query', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@tanstack/svelte-query')>();
    return { ...actual, createMutation: vi.fn(), useQueryClient: vi.fn() };
});

const { trackEvent } = vi.hoisted(() => ({ trackEvent: vi.fn() }));
vi.mock('$lib/hooks/usePostHog', () => ({
    usePostHog: () => ({ trackEvent })
}));

describe('useUpdateAnnotationsMutation', () => {
    const invalidateQueries = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(useQueryClient).mockReturnValue({
            invalidateQueries
        } as unknown as ReturnType<typeof useQueryClient>);
    });

    it('fires annotation_label_updated when a single update with label_name succeeds', async () => {
        vi.mocked(createMutation).mockReturnValue({
            mutate: (_vars: unknown, opts: { onSuccess: () => void }) => {
                opts.onSuccess();
            }
        } as unknown as ReturnType<typeof createMutation>);

        const { updateAnnotations } = useUpdateAnnotationsMutation({
            getCollectionId: () => 'col-1'
        });
        await updateAnnotations([
            { annotation_id: 'ann-1', collection_id: 'col-1', label_name: 'dog' }
        ]);

        expect(trackEvent).toHaveBeenCalledWith('annotation_label_updated', {
            collection_id: 'col-1',
            annotation_id: 'ann-1',
            label_name: 'dog'
        });
    });

    it('fires annotations_bulk_labeled for multiple updates with label_names', async () => {
        vi.mocked(createMutation).mockReturnValue({
            mutate: (_vars: unknown, opts: { onSuccess: () => void }) => {
                opts.onSuccess();
            }
        } as unknown as ReturnType<typeof createMutation>);

        const { updateAnnotations } = useUpdateAnnotationsMutation({
            getCollectionId: () => 'col-1'
        });
        await updateAnnotations([
            { annotation_id: 'ann-1', collection_id: 'col-1', label_name: 'dog' },
            { annotation_id: 'ann-2', collection_id: 'col-1', label_name: 'cat' }
        ]);

        expect(trackEvent).toHaveBeenCalledWith('annotations_bulk_labeled', {
            collection_id: 'col-1',
            annotation_ids: ['ann-1', 'ann-2'],
            annotation_count: 2
        });
    });

    it('fires annotation_label_updated with label_name undefined when a single update has no label_name', async () => {
        vi.mocked(createMutation).mockReturnValue({
            mutate: (_vars: unknown, opts: { onSuccess: () => void }) => {
                opts.onSuccess();
            }
        } as unknown as ReturnType<typeof createMutation>);

        const { updateAnnotations } = useUpdateAnnotationsMutation({
            getCollectionId: () => 'col-1'
        });
        await updateAnnotations([
            {
                annotation_id: 'ann-1',
                collection_id: 'col-1',
                bounding_box: { x: 0, y: 0, width: 10, height: 10 }
            }
        ]);

        expect(trackEvent).toHaveBeenCalledWith('annotation_label_updated', {
            collection_id: 'col-1',
            annotation_id: 'ann-1',
            label_name: undefined
        });
    });
});
