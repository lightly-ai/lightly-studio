import { beforeEach, describe, expect, it, vi } from 'vitest';
import { toast } from 'svelte-sonner';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useDeleteAnnotationWithUndo } from './useDeleteAnnotationWithUndo.svelte';

const mocks = vi.hoisted(() => ({
    deleteAnnotation: vi.fn(),
    addDeleteToUndoStack: vi.fn(),
    sources: [] as unknown[] | undefined
}));

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({ data: [{ annotation_label_id: 'l1' }] })
}));
vi.mock('$lib/hooks/useAnnotationCollections/useAnnotationCollections', () => ({
    useAnnotationCollections: () => ({ data: mocks.sources })
}));
vi.mock('$lib/hooks/useCreateAnnotation/useCreateAnnotation', () => ({
    useCreateAnnotation: () => ({ createAnnotation: vi.fn() })
}));
vi.mock('$lib/hooks/useDeleteAnnotation/useDeleteAnnotation', () => ({
    useDeleteAnnotation: () => ({ deleteAnnotation: mocks.deleteAnnotation })
}));
vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({ addReversibleAction: vi.fn() })
}));
vi.mock('$lib/services/addAnnotationDeleteToUndoStack', () => ({
    addAnnotationDeleteToUndoStack: mocks.addDeleteToUndoStack
}));
vi.mock('svelte-sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const annotation = { sample_id: 'a1', annotation_type: 'object_detection' } as AnnotationView;

describe('useDeleteAnnotationWithUndo', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.sources = [];
    });

    it('adds the undo after the delete succeeded', async () => {
        const refetch = vi.fn();
        const { deleteWithUndo } = useDeleteAnnotationWithUndo(() => 'col-1');

        expect(await deleteWithUndo(annotation, refetch)).toBe(true);

        expect(mocks.addDeleteToUndoStack).toHaveBeenCalledOnce();
        expect(refetch).toHaveBeenCalled();
    });

    it('adds no undo when the delete fails', async () => {
        mocks.deleteAnnotation.mockRejectedValueOnce(new Error('offline'));
        const { deleteWithUndo } = useDeleteAnnotationWithUndo(() => 'col-1');

        expect(await deleteWithUndo(annotation, vi.fn())).toBe(false);

        expect(mocks.addDeleteToUndoStack).not.toHaveBeenCalled();
    });

    it('shows no delete error when the refetch after a delete throws', async () => {
        const refetch = vi.fn(() => {
            throw new Error('refetch failed');
        });
        const { deleteWithUndo } = useDeleteAnnotationWithUndo(() => 'col-1');

        await expect(deleteWithUndo(annotation, refetch)).rejects.toThrow('refetch failed');

        expect(mocks.addDeleteToUndoStack).toHaveBeenCalledOnce();
        expect(toast.error).not.toHaveBeenCalled();
    });

    it('deletes once while a delete runs', async () => {
        let finish = () => {};
        mocks.deleteAnnotation.mockReturnValueOnce(new Promise<void>((r) => (finish = r)));
        const { deleteWithUndo } = useDeleteAnnotationWithUndo(() => 'col-1');

        const first = deleteWithUndo(annotation, vi.fn());
        expect(await deleteWithUndo(annotation, vi.fn())).toBe(false);
        finish();
        await first;

        expect(mocks.deleteAnnotation).toHaveBeenCalledOnce();
        expect(mocks.addDeleteToUndoStack).toHaveBeenCalledOnce();
    });

    it('deletes another annotation while a delete runs', async () => {
        let finish = () => {};
        mocks.deleteAnnotation.mockReturnValueOnce(new Promise<void>((r) => (finish = r)));
        const { deleteWithUndo } = useDeleteAnnotationWithUndo(() => 'col-1');

        const first = deleteWithUndo(annotation, vi.fn());
        expect(await deleteWithUndo({ ...annotation, sample_id: 'a2' }, vi.fn())).toBe(true);
        finish();
        await first;

        expect(mocks.deleteAnnotation).toHaveBeenCalledTimes(2);
    });

    it('deletes nothing while the sources load', async () => {
        mocks.sources = undefined;
        const { deleteWithUndo } = useDeleteAnnotationWithUndo(() => 'col-1');

        expect(await deleteWithUndo(annotation, vi.fn())).toBe(false);

        expect(mocks.deleteAnnotation).not.toHaveBeenCalled();
    });
});
