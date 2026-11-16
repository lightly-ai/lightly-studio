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

const { trackEvent } = vi.hoisted(() => ({ trackEvent: vi.fn() }));
vi.mock('$lib/hooks/usePostHog', () => ({
    usePostHog: () => ({ trackEvent })
}));

vi.mock('$app/state', () => ({
    page: { params: { collection_type: 'images' } }
}));

const { invalidateAnnotationGridQueries, useInvalidateAnnotationGridQueries } = vi.hoisted(() => ({
    invalidateAnnotationGridQueries: vi.fn(),
    useInvalidateAnnotationGridQueries: vi.fn()
}));
vi.mock('$lib/hooks/useInvalidateAnnotationGridQueries', () => ({
    useInvalidateAnnotationGridQueries
}));

describe('useCreateAnnotation', () => {
    const invalidateQueries = vi.fn();
    const mockMutateAsync = vi.fn();
    const created = {
        sample_id: 'created-annotation',
        annotation_type: 'object_detection',
        annotation_label: { annotation_label_name: 'car' }
    };

    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(createMutation).mockReturnValue({
            mutateAsync: mockMutateAsync
        } as unknown as ReturnType<typeof createMutation>);
        useInvalidateAnnotationGridQueries.mockReturnValue(invalidateAnnotationGridQueries);
        vi.mocked(useQueryClient).mockReturnValue({
            invalidateQueries
        } as unknown as ReturnType<typeof useQueryClient>);
    });

    it('invalidates annotation-bearing grids, counts, and sources after a successful create', async () => {
        mockMutateAsync.mockResolvedValue(created);

        const { createAnnotation } = useCreateAnnotation({ getCollectionId: () => 'col-1' });
        await createAnnotation({
            parent_sample_id: 's1',
            annotation_type: 'classification',
            annotation_label_id: 'l1'
        } as AnnotationCreateInput);

        expect(invalidateQueries).toHaveBeenCalledWith({
            queryKey: useImageAnnotationCountsQueryKey
        });
        expect(useInvalidateAnnotationGridQueries).toHaveBeenCalledWith();
        expect(invalidateAnnotationGridQueries).toHaveBeenCalledWith('col-1');
        expect(invalidateQueries).toHaveBeenCalledWith({
            queryKey: readAnnotationCollectionsQueryKey({ path: { collection_id: 'col-1' } })
        });
        expect(invalidateQueries).toHaveBeenCalledWith({
            queryKey: [{ _id: 'getEvaluationRuns' }]
        });
    });

    it('fires annotation_created with correct properties on success', async () => {
        mockMutateAsync.mockResolvedValue(created);

        const { createAnnotation } = useCreateAnnotation({ getCollectionId: () => 'col-1' });
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

    it('calls mutateAsync with only the variables and returns the response', async () => {
        mockMutateAsync.mockResolvedValue(created);
        const inputs = {
            parent_sample_id: 's1',
            annotation_type: 'object_detection',
            annotation_label_id: 'l1'
        } as AnnotationCreateInput;

        const { createAnnotation } = useCreateAnnotation({ getCollectionId: () => 'col-1' });
        const result = await createAnnotation(inputs);

        expect(result).toBe(created);
        expect(mockMutateAsync).toHaveBeenCalledTimes(1);
        expect(mockMutateAsync.mock.calls[0]).toEqual([
            { path: { collection_id: 'col-1' }, body: inputs }
        ]);
        expect(invalidateAnnotationGridQueries).toHaveBeenCalledTimes(1);
        expect(trackEvent).toHaveBeenCalledTimes(1);
    });

    it('rejects with the same error and does not refetch when mutateAsync rejects', async () => {
        const error = new Error('boom');
        mockMutateAsync.mockRejectedValue(error);

        const { createAnnotation } = useCreateAnnotation({ getCollectionId: () => 'col-1' });

        await expect(createAnnotation({} as AnnotationCreateInput)).rejects.toBe(error);
        expect(invalidateAnnotationGridQueries).not.toHaveBeenCalled();
        expect(invalidateQueries).not.toHaveBeenCalled();
        expect(trackEvent).not.toHaveBeenCalled();
    });
});
