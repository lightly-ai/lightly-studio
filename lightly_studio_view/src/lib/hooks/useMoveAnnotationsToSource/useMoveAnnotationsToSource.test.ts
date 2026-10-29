import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useMoveAnnotationsToSource } from './useMoveAnnotationsToSource';

const mocks = vi.hoisted(() => ({
    invalidateQueries: vi.fn(),
    moveAnnotations: vi.fn(),
    toastSuccess: vi.fn(),
    toastError: vi.fn()
}));

vi.mock('@tanstack/svelte-query', () => ({
    useQueryClient: () => ({ invalidateQueries: mocks.invalidateQueries })
}));

vi.mock('$lib/api/lightly_studio_local', () => ({
    moveAnnotations: mocks.moveAnnotations
}));

vi.mock('svelte-sonner', () => ({
    toast: { success: mocks.toastSuccess, error: mocks.toastError }
}));

const input = { collectionId: 'col-1', annotationIds: ['a', 'b'], sourceName: 'ground_truth' };

describe('useMoveAnnotationsToSource', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('moves the annotations and refetches', async () => {
        mocks.moveAnnotations.mockResolvedValue({
            data: { annotation_collection_id: 's1', moved_count: 2 }
        });
        const { moveToSource } = useMoveAnnotationsToSource();

        const moved = await moveToSource(input);

        expect(moved).toBe(true);
        expect(mocks.moveAnnotations).toHaveBeenCalledWith({
            path: { collection_id: 'col-1' },
            body: { annotation_ids: ['a', 'b'], target_annotation_collection_name: 'ground_truth' }
        });
        expect(mocks.invalidateQueries).toHaveBeenCalledOnce();
        expect(mocks.toastSuccess).toHaveBeenCalledWith('Moved 2 annotations to “ground_truth”');
    });

    it('shows the server error when the move fails', async () => {
        mocks.moveAnnotations.mockResolvedValue({
            error: { error: 'Annotation source x not found.' }
        });
        const { moveToSource } = useMoveAnnotationsToSource();

        const moved = await moveToSource(input);

        expect(moved).toBe(false);
        expect(mocks.invalidateQueries).not.toHaveBeenCalled();
        expect(mocks.toastError).toHaveBeenCalledWith('Annotation source x not found.');
    });

    it('does nothing without annotations', async () => {
        const { moveToSource } = useMoveAnnotationsToSource();

        expect(await moveToSource({ ...input, annotationIds: [] })).toBe(false);
        expect(mocks.moveAnnotations).not.toHaveBeenCalled();
    });
});
