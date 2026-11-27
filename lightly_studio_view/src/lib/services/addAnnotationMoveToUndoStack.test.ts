import { describe, expect, it, vi } from 'vitest';
import type { AnnotationCreateInput } from '$lib/api/lightly_studio_local';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';
import {
    ANNOTATION_MOVE_GROUP_ID,
    addAnnotationMoveToUndoStack
} from './addAnnotationMoveToUndoStack';

const original: AnnotationCreateInput = {
    annotation_label_id: 'class',
    annotation_type: 'object_detection',
    annotation_collection_name: 'predictions',
    parent_sample_id: 'image',
    x: 1,
    y: 2,
    width: 3,
    height: 4
};

const setup = (
    restore: AnnotationCreateInput | null,
    ids: { copyId?: string; originalId?: string; restoredId?: string } = {}
) => {
    const actions: ReversibleAction[] = [];
    const createAnnotation = vi.fn().mockResolvedValue({ sample_id: ids.restoredId ?? 'restored' });
    const deleteAnnotation = vi.fn().mockResolvedValue(undefined);
    const refetch = vi.fn();
    addAnnotationMoveToUndoStack({
        copy: { sample_id: ids.copyId ?? 'copy', annotation_type: 'object_detection' },
        original: restore,
        originalId: ids.originalId ?? 'original',
        addReversibleAction: (action) => actions.push(action),
        createAnnotation,
        deleteAnnotation,
        refetch
    });
    return { action: actions[0], createAnnotation, deleteAnnotation, refetch };
};

describe('addAnnotationMoveToUndoStack', () => {
    it('re-creates the original in its source, then deletes the copy', async () => {
        const { action, createAnnotation, deleteAnnotation, refetch } = setup(original);
        expect(action.groupId).toBe(ANNOTATION_MOVE_GROUP_ID);

        await action.execute();

        expect(createAnnotation).toHaveBeenCalledExactlyOnceWith(original);
        expect(deleteAnnotation).toHaveBeenCalledExactlyOnceWith('copy', 'object_detection');
        expect(createAnnotation.mock.invocationCallOrder[0]).toBeLessThan(
            deleteAnnotation.mock.invocationCallOrder[0]
        );
        expect(refetch).toHaveBeenCalledOnce();
    });

    it('only deletes the copy when the move kept the original', async () => {
        const { action, createAnnotation, deleteAnnotation } = setup(null);

        await action.execute();

        expect(createAnnotation).not.toHaveBeenCalled();
        expect(deleteAnnotation).toHaveBeenCalledExactlyOnceWith('copy', 'object_detection');
    });

    it('keeps the copy when the original cannot be re-created', async () => {
        const { action, createAnnotation, deleteAnnotation } = setup(original);
        createAnnotation.mockRejectedValue(new Error('offline'));

        await expect(action.execute()).rejects.toThrow('offline');

        expect(deleteAnnotation).not.toHaveBeenCalled();
    });

    it('deletes the copy once when a retry follows a failed delete', async () => {
        const { action, createAnnotation, deleteAnnotation } = setup(original);
        deleteAnnotation.mockRejectedValueOnce(new Error('offline'));

        await expect(action.execute()).rejects.toThrow('offline');
        await action.execute();

        expect(createAnnotation).toHaveBeenCalledOnce();
        expect(deleteAnnotation).toHaveBeenCalledTimes(2);
    });

    it('deletes the re-created annotation when undoing the move before it', async () => {
        // The annotation moved from source A to B, and then from B to C.
        const toB = setup(original, { originalId: 'a', copyId: 'b', restoredId: 'a-again' });
        const toC = setup(original, { originalId: 'b', copyId: 'c', restoredId: 'b-again' });

        await toC.action.execute();
        await toB.action.execute();

        expect(toC.deleteAnnotation).toHaveBeenCalledExactlyOnceWith('c', 'object_detection');
        expect(toB.deleteAnnotation).toHaveBeenCalledExactlyOnceWith('b-again', 'object_detection');
    });
});
