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

const setup = (restore: AnnotationCreateInput | null) => {
    const actions: ReversibleAction[] = [];
    const createAnnotation = vi.fn().mockResolvedValue({ sample_id: 'restored' });
    const deleteAnnotation = vi.fn().mockResolvedValue(undefined);
    const refetch = vi.fn();
    addAnnotationMoveToUndoStack({
        copy: { sample_id: 'copy', annotation_type: 'object_detection' },
        original: restore,
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
});
