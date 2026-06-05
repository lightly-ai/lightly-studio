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
                opts.onSuccess({ sample_id: 'created-annotation' });
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
});
