import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useAnnotationCardActions } from './useAnnotationCardActions.svelte';

const mocks = vi.hoisted(() => ({
    deleteAnnotation: vi.fn(),
    addDeleteToUndoStack: vi.fn(),
    setAnnotationId: vi.fn()
}));

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({ setAnnotationId: mocks.setAnnotationId })
}));
vi.mock('$lib/hooks', () => ({
    useAnnotationCollections: () => ({ data: [] }),
    useMoveAnnotationsToSource: () => ({ moveToSource: vi.fn(), isPending: false }),
    useStickyClass: () => ({ pickClass: vi.fn() })
}));
vi.mock('$lib/hooks/useAnnotation/useAnnotation', () => ({
    useAnnotation: () => ({ updateAnnotation: vi.fn() })
}));
vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({ data: [] })
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
vi.mock('$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation', () => ({
    useUpdateAnnotationsMutation: () => ({ updateAnnotations: vi.fn() })
}));
vi.mock('$lib/services/addAnnotationDeleteToUndoStack', () => ({
    addAnnotationDeleteToUndoStack: mocks.addDeleteToUndoStack
}));
vi.mock('svelte-sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const annotation = {
    sample_id: 'a1',
    annotation_type: 'object_detection'
} as unknown as AnnotationView;

const setup = () =>
    useAnnotationCardActions(() => ({ collectionId: 'col-1', annotation, refetch: vi.fn() }));

describe('useAnnotationCardActions', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('sends one delete when Delete is pressed again before the first one finishes', async () => {
        let finishDelete!: () => void;
        mocks.deleteAnnotation.mockReturnValue(new Promise<void>((r) => (finishDelete = r)));
        const { remove } = setup();

        const first = remove();
        const second = remove();
        finishDelete();
        await Promise.all([first, second]);

        expect(mocks.deleteAnnotation).toHaveBeenCalledOnce();
        expect(mocks.addDeleteToUndoStack).toHaveBeenCalledOnce();
    });

    it('adds the undo entry only after the delete succeeds', async () => {
        mocks.deleteAnnotation.mockRejectedValue(new Error('boom'));
        const { remove } = setup();

        await remove();

        expect(mocks.addDeleteToUndoStack).not.toHaveBeenCalled();
        expect(mocks.setAnnotationId).not.toHaveBeenCalled();
    });

    it('deletes again after a failed delete', async () => {
        mocks.deleteAnnotation.mockRejectedValueOnce(new Error('boom'));
        mocks.deleteAnnotation.mockResolvedValueOnce(undefined);
        const { remove } = setup();

        await remove();
        await remove();

        expect(mocks.deleteAnnotation).toHaveBeenCalledTimes(2);
        expect(mocks.addDeleteToUndoStack).toHaveBeenCalledOnce();
    });
});
