import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { readAnnotationCollectionsQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';
import type { AnnotationCreateInput } from '$lib/api/lightly_studio_local';
import { useCreateAnnotation } from './useCreateAnnotation';

// Keep the generated query-key helpers real; only swap the query/mutation runtime so the
// hook can run outside a QueryClientProvider and we can drive onSuccess synchronously.
vi.mock('@tanstack/svelte-query', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@tanstack/svelte-query')>();
    return { ...actual, createMutation: vi.fn(), useQueryClient: vi.fn() };
});

const trackEvent = vi.fn();
vi.mock('$lib/hooks/usePostHog', () => ({
    usePostHog: () => ({ trackEvent })
}));

vi.mock('$app/state', () => ({
    page: { params: { collection_type: 'images' } }
}));

describe('useCreateAnnotation', () => {
    const invalidateQueries = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(useQueryClient).mockReturnValue({
            invalidateQueries
        } as unknown as ReturnType<typeof useQueryClient>);
    });

    it('invalidates the annotation counts and the source list after a successful create', async () => {
        vi.mocked(createMutation).mockReturnValue({
            mutate: (_vars: unknown, opts: { onSuccess: (data: unknown) => void }) => {
                opts.onSuccess({
                    sample_id: 'created-annotation',
                    annotation_type: 'object_detection',
                    annotation_label: { annotation_label_name: 'car' }
                });
            }
        } as unknown as ReturnType<typeof createMutation>);

        const { createAnnotation } = useCreateAnnotation({ collectionId: 'col-1' });
        await createAnnotation({
            parent_sample_id: 's1',
            annotation_type: 'classification',
            annotation_label_id: 'l1'
        } as AnnotationCreateInput);

        expect(invalidateQueries).toHaveBeenCalledWith({
            queryKey: useImageAnnotationCountsQueryKey
        });
        expect(invalidateQueries).toHaveBeenCalledWith({
            queryKey: readAnnotationCollectionsQueryKey({ path: { collection_id: 'col-1' } })
        });
    });

    it('fires annotation_created with correct properties on success', async () => {
        vi.mocked(createMutation).mockReturnValue({
            mutate: (_vars: unknown, opts: { onSuccess: (data: unknown) => void }) => {
                opts.onSuccess({
                    sample_id: 'created-annotation',
                    annotation_type: 'object_detection',
                    annotation_label: { annotation_label_name: 'car' }
                });
            }
        } as unknown as ReturnType<typeof createMutation>);

        const { createAnnotation } = useCreateAnnotation({ collectionId: 'col-1' });
        await createAnnotation({
            parent_sample_id: 's1',
            annotation_type: 'object_detection',
            annotation_label_id: 'l1'
        } as AnnotationCreateInput);

        expect(trackEvent).toHaveBeenCalledWith('annotation_created', {
            collection_id: 'col-1',
            annotation_type: 'object_detection',
            parent_sample_type: 'images',
            label_name: 'car'
        });
    });
});
