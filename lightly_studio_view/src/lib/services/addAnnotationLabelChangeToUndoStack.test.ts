import { describe, it, expect, vi } from 'vitest';
import { addAnnotationLabelChangeToUndoStack } from './addAnnotationLabelChangeToUndoStack';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';

describe('addAnnotationLabelChangeToUndoStack', () => {
    const mockAnnotations = [
        {
            sample_id: 'annotation-1',
            annotation_label: { annotation_label_name: 'car' }
        },
        {
            sample_id: 'annotation-2',
            annotation_label: { annotation_label_name: 'truck' }
        }
    ];

    it('should add a reversible action to undo stack', () => {
        const addReversibleAction = vi.fn();
        const updateAnnotations = vi.fn().mockResolvedValue(undefined);
        const refresh = vi.fn();

        addAnnotationLabelChangeToUndoStack({
            annotations: mockAnnotations,
            collectionId: 'collection-123',
            addReversibleAction,
            updateAnnotations,
            refresh
        });

        expect(addReversibleAction).toHaveBeenCalledTimes(1);
        const action = addReversibleAction.mock.calls[0][0] as ReversibleAction;
        expect(action.id).toContain('annotation-label-change');
        expect(action.description).toBe('Undo label change for 2 annotations');
        expect(action.groupId).toBe('annotation-label-change');
    });

    it('should use singular form for single annotation', () => {
        const addReversibleAction = vi.fn();
        const updateAnnotations = vi.fn().mockResolvedValue(undefined);
        const refresh = vi.fn();

        addAnnotationLabelChangeToUndoStack({
            annotations: [mockAnnotations[0]],
            collectionId: 'collection-123',
            addReversibleAction,
            updateAnnotations,
            refresh
        });

        const action = addReversibleAction.mock.calls[0][0] as ReversibleAction;
        expect(action.description).toBe('Undo label change for 1 annotation');
    });

    it('should call updateAnnotations with previous labels and refresh when executed', async () => {
        const addReversibleAction = vi.fn();
        const updateAnnotations = vi.fn().mockResolvedValue(undefined);
        const refresh = vi.fn();

        addAnnotationLabelChangeToUndoStack({
            annotations: mockAnnotations,
            collectionId: 'collection-123',
            addReversibleAction,
            updateAnnotations,
            refresh
        });

        const action = addReversibleAction.mock.calls[0][0] as ReversibleAction;
        await action.execute();

        expect(updateAnnotations).toHaveBeenCalledWith([
            { annotation_id: 'annotation-1', label_name: 'car', collection_id: 'collection-123' },
            { annotation_id: 'annotation-2', label_name: 'truck', collection_id: 'collection-123' }
        ]);
        expect(refresh).toHaveBeenCalled();
    });
});
