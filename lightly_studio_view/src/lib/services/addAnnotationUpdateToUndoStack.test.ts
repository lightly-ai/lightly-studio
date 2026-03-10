import { describe, it, expect, vi } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';
import { addAnnotationUpdateToUndoStack } from './addAnnotationUpdateToUndoStack';

vi.mock('$lib/components/SampleAnnotation/utils', () => ({
    getBoundingBox: vi.fn(() => ({ x: 1, y: 2, width: 3, height: 4 }))
}));

describe('addAnnotationUpdateToUndoStack', () => {
    const annotation = {
        sample_id: 'annotation-id',
        annotation_type: 'semantic_segmentation',
        annotation_label: {
            annotation_label_name: 'car'
        },
        segmentation_details: {
            x: 1,
            y: 2,
            width: 3,
            height: 4,
            segmentation_mask: [1, 0, 2]
        }
    } as AnnotationView;

    it('adds undo action and reverts annotation update', async () => {
        const addReversibleAction = vi.fn();
        const updateAnnotation = vi.fn().mockResolvedValue(undefined);

        addAnnotationUpdateToUndoStack({
            annotation,
            collection_id: 'collection-id',
            addReversibleAction,
            updateAnnotation
        });

        const action = addReversibleAction.mock.calls[0][0] as ReversibleAction;
        await action.execute();

        expect(updateAnnotation).toHaveBeenCalledWith({
            annotation_id: 'annotation-id',
            collection_id: 'collection-id',
            bounding_box: { x: 1, y: 2, width: 3, height: 4 },
            segmentation_mask: [1, 0, 2]
        });
    });

    it('runs optional onUndo callback after restoring annotation', async () => {
        const addReversibleAction = vi.fn();
        const updateAnnotation = vi.fn().mockResolvedValue(undefined);
        const onUndo = vi.fn().mockResolvedValue(undefined);

        addAnnotationUpdateToUndoStack({
            annotation,
            collection_id: 'collection-id',
            addReversibleAction,
            updateAnnotation,
            onUndo
        });

        const action = addReversibleAction.mock.calls[0][0] as ReversibleAction;
        await action.execute();

        expect(onUndo).toHaveBeenCalledTimes(1);
        expect(updateAnnotation.mock.invocationCallOrder[0]).toBeLessThan(
            onUndo.mock.invocationCallOrder[0]
        );
    });
});
