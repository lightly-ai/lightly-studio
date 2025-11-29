import { describe, it, expect, vi } from 'vitest';
import { addAnnotationCreateToUndoStack } from './addAnnotationCreateToUndoStack';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';

describe('addAnnotationCreateToUndoStack', () => {
    const mockAnnotation: AnnotationView = {
        sample_id: 'annotation-123',
        parent_sample_id: 'sample-456',
        dataset_id: 'dataset-789',
        annotation_type: 'object_detection',
        annotation_label: {
            annotation_label_name: 'car'
        },
        created_at: new Date()
    };

    it('should add a reversible action to undo stack', () => {
        const addReversibleAction = vi.fn();
        const deleteAnnotation = vi.fn().mockResolvedValue(undefined);
        const refetch = vi.fn();

        addAnnotationCreateToUndoStack({
            annotation: mockAnnotation,
            addReversibleAction,
            deleteAnnotation,
            refetch
        });

        expect(addReversibleAction).toHaveBeenCalledTimes(1);
        const action = addReversibleAction.mock.calls[0][0] as ReversibleAction;
        expect(action.id).toContain('annotation-create-annotation-123');
        expect(action.description).toBe('Undo create annotation');
        expect(action.groupId).toBe('annotation-create');
    });

    it('should call deleteAnnotation and refetch when execute is called', async () => {
        const addReversibleAction = vi.fn();
        const deleteAnnotation = vi.fn().mockResolvedValue(undefined);
        const refetch = vi.fn();

        addAnnotationCreateToUndoStack({
            annotation: mockAnnotation,
            addReversibleAction,
            deleteAnnotation,
            refetch
        });

        const action = addReversibleAction.mock.calls[0][0] as ReversibleAction;
        await action.execute();

        expect(deleteAnnotation).toHaveBeenCalledWith('annotation-123');
        expect(refetch).toHaveBeenCalled();
    });
});
