import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useAnnotationCardActions } from './useAnnotationCardActions.svelte';

const mocks = vi.hoisted(() => ({
    deleteAnnotation: vi.fn(),
    addDeleteToUndoStack: vi.fn(),
    setAnnotationId: vi.fn(),
    updateAnnotations: vi.fn(),
    addLabelChangeToUndoStack: vi.fn(),
    pickClass: vi.fn(),
    moveByCopy: vi.fn(),
    refetch: vi.fn()
}));

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({
        setAnnotationId: mocks.setAnnotationId,
        setAnnotationLabel: vi.fn()
    })
}));
vi.mock('$lib/hooks/useAnnotationCollections/useAnnotationCollections', () => ({
    useAnnotationCollections: () => ({ data: [] })
}));
vi.mock('$lib/hooks', async () => ({
    useAnnotation: () => ({ refetch: vi.fn() }),
    useGlobalStorage: () => ({ addReversibleAction: vi.fn() }),
    useUpdateAnnotationsMutation: () => ({ updateAnnotations: mocks.updateAnnotations }),
    useAnnotationCollections: () => ({ data: [] }),
    useStickyClass: () => ({ pickClass: mocks.pickClass }),
    useDeleteAnnotationWithUndo: (
        await import('$lib/hooks/useDeleteAnnotationWithUndo/useDeleteAnnotationWithUndo.svelte')
    ).useDeleteAnnotationWithUndo
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
vi.mock('$lib/services/addAnnotationDeleteToUndoStack', () => ({
    addAnnotationDeleteToUndoStack: mocks.addDeleteToUndoStack
}));
vi.mock('$lib/services/addAnnotationLabelChangeToUndoStack', () => ({
    addAnnotationLabelChangeToUndoStack: mocks.addLabelChangeToUndoStack
}));
vi.mock('./useMoveAnnotationByCopy.svelte', () => ({
    useMoveAnnotationByCopy: () => ({ moveByCopy: mocks.moveByCopy })
}));
vi.mock('svelte-sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const annotation = {
    sample_id: 'a1',
    annotation_type: 'object_detection',
    annotation_label: { annotation_label_name: 'bobcat' }
} as unknown as AnnotationView;

const setup = () =>
    useAnnotationCardActions(() => ({ collectionId: 'col-1', annotation, refetch: mocks.refetch }));

describe('useAnnotationCardActions', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('follows the copy after a move', async () => {
        mocks.moveByCopy.mockResolvedValue('copy');
        const { moveTo } = setup();

        expect(await moveTo('gt')).toBe(true);

        expect(mocks.moveByCopy).toHaveBeenCalledWith(annotation, 'gt');
        expect(mocks.setAnnotationId).toHaveBeenCalledWith('copy');
        expect(mocks.refetch).toHaveBeenCalled();
    });

    it('stays on the original when nothing was copied', async () => {
        mocks.moveByCopy.mockResolvedValue(null);
        const { moveTo } = setup();

        expect(await moveTo('gt')).toBe(false);

        expect(mocks.setAnnotationId).not.toHaveBeenCalled();
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

    it('records the class change only after the update succeeds', async () => {
        mocks.updateAnnotations.mockRejectedValue(new Error('boom'));
        const { changeClass } = setup();

        await changeClass('coyote');

        expect(mocks.updateAnnotations).toHaveBeenCalledOnce();
        expect(mocks.addLabelChangeToUndoStack).not.toHaveBeenCalled();
        expect(mocks.pickClass).not.toHaveBeenCalled();
    });

    it('records a successful class change once', async () => {
        mocks.updateAnnotations.mockResolvedValue(undefined);
        const { changeClass } = setup();

        await changeClass('coyote');

        expect(mocks.updateAnnotations).toHaveBeenCalledWith([
            { annotation_id: 'a1', collection_id: 'col-1', label_name: 'coyote' }
        ]);
        expect(mocks.addLabelChangeToUndoStack).toHaveBeenCalledOnce();
        expect(mocks.pickClass).toHaveBeenCalledWith('col-1', 'coyote');
    });

    it('sends one update when a class is picked again before the first one finishes', async () => {
        let finishUpdate!: () => void;
        mocks.updateAnnotations.mockReturnValue(new Promise<void>((r) => (finishUpdate = r)));
        const { changeClass } = setup();

        const first = changeClass('coyote');
        const second = changeClass('coyote');
        finishUpdate();
        await Promise.all([first, second]);

        expect(mocks.updateAnnotations).toHaveBeenCalledOnce();
        expect(mocks.addLabelChangeToUndoStack).toHaveBeenCalledOnce();
    });

    it('refuses a move and a delete while a class change runs', async () => {
        let finishUpdate!: () => void;
        mocks.updateAnnotations.mockReturnValue(new Promise<void>((r) => (finishUpdate = r)));
        const { changeClass, moveTo, remove } = setup();

        const change = changeClass('coyote');
        expect(await moveTo('gt')).toBe(false);
        await remove();
        finishUpdate();
        await change;

        expect(mocks.moveByCopy).not.toHaveBeenCalled();
        expect(mocks.deleteAnnotation).not.toHaveBeenCalled();
    });

    it('does nothing when the class is unchanged', async () => {
        const { changeClass } = setup();

        await changeClass('bobcat');

        expect(mocks.updateAnnotations).not.toHaveBeenCalled();
        expect(mocks.addLabelChangeToUndoStack).not.toHaveBeenCalled();
    });
});
