import { describe, it, expect, vi } from 'vitest';
import { addAnnotationDeleteToUndoStack } from './addAnnotationDeleteToUndoStack';
import type {
    AnnotationLabelTable,
    AnnotationView,
    CreateAnnotationResponse
} from '$lib/api/lightly_studio_local';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';

describe('addAnnotationDeleteToUndoStack', () => {
    const mockAnnotation: AnnotationView = {
        sample_id: 'annotation-123',
        parent_sample_id: 'sample-456',
        collection_id: 'collection-789',
        annotation_type: 'object_detection',
        annotation_label: {
            annotation_label_name: 'car'
        },
        object_detection_details: {
            x: 10,
            y: 20,
            width: 100,
            height: 50
        },
        created_at: new Date()
    };

    const mockLabels: AnnotationLabelTable[] = [
        {
            annotation_label_name: 'car',
            annotation_label_id: 'label-id-car'
        },
        {
            annotation_label_name: 'person',
            annotation_label_id: 'label-id-person'
        }
    ];

    it('should add a reversible action to undo stack', () => {
        const addReversibleAction = vi.fn();
        const createAnnotation = vi.fn().mockResolvedValue({} as CreateAnnotationResponse);
        const refetch = vi.fn();

        addAnnotationDeleteToUndoStack({
            annotation: mockAnnotation,
            labels: mockLabels,
            addReversibleAction,
            createAnnotation,
            refetch
        });

        expect(addReversibleAction).toHaveBeenCalledTimes(1);
        const action = addReversibleAction.mock.calls[0][0] as ReversibleAction;
        expect(action.id).toContain('annotation-delete-annotation-123');
        expect(action.description).toBe('Undo delete annotation');
        expect(action.groupId).toBe('annotation-delete');
    });

    it('should call createAnnotation and refetch when execute is called', async () => {
        const addReversibleAction = vi.fn();
        const createAnnotation = vi.fn().mockResolvedValue({} as CreateAnnotationResponse);
        const refetch = vi.fn();

        addAnnotationDeleteToUndoStack({
            annotation: mockAnnotation,
            labels: mockLabels,
            addReversibleAction,
            createAnnotation,
            refetch
        });

        const action = addReversibleAction.mock.calls[0][0] as ReversibleAction;
        await action.execute();

        expect(createAnnotation).toHaveBeenCalledWith({
            parent_sample_id: 'sample-456',
            annotation_type: 'object_detection',
            annotation_label_id: 'label-id-car',
            x: 10,
            y: 20,
            width: 100,
            height: 50,
            segmentation_mask: undefined
        });
        expect(refetch).toHaveBeenCalled();
    });

    it('should not add action if label is not found', () => {
        const addReversibleAction = vi.fn();
        const createAnnotation = vi.fn().mockResolvedValue({} as CreateAnnotationResponse);
        const refetch = vi.fn();

        const annotationWithUnknownLabel: AnnotationView = {
            ...mockAnnotation,
            annotation_label: {
                annotation_label_name: 'unknown-label'
            }
        };

        addAnnotationDeleteToUndoStack({
            annotation: annotationWithUnknownLabel,
            labels: mockLabels,
            addReversibleAction,
            createAnnotation,
            refetch
        });

        expect(addReversibleAction).not.toHaveBeenCalled();
    });

    it('should not add action if label has no ID', () => {
        const addReversibleAction = vi.fn();
        const createAnnotation = vi.fn().mockResolvedValue({} as CreateAnnotationResponse);
        const refetch = vi.fn();

        const labelsWithoutId: AnnotationLabelTable[] = [
            {
                annotation_label_name: 'car'
            }
        ];

        addAnnotationDeleteToUndoStack({
            annotation: mockAnnotation,
            labels: labelsWithoutId,
            addReversibleAction,
            createAnnotation,
            refetch
        });

        expect(addReversibleAction).not.toHaveBeenCalled();
    });

    it('should handle instance segmentation annotations', async () => {
        const addReversibleAction = vi.fn();
        const createAnnotation = vi.fn().mockResolvedValue({} as CreateAnnotationResponse);
        const refetch = vi.fn();

        const segmentationAnnotation: AnnotationView = {
            ...mockAnnotation,
            annotation_type: 'instance_segmentation',
            object_detection_details: undefined,
            segmentation_details: {
                x: 15,
                y: 25,
                width: 200,
                height: 150,
                segmentation_mask: [1, 2, 3, 4, 5]
            }
        };

        addAnnotationDeleteToUndoStack({
            annotation: segmentationAnnotation,
            labels: mockLabels,
            addReversibleAction,
            createAnnotation,
            refetch
        });

        const action = addReversibleAction.mock.calls[0][0] as ReversibleAction;
        await action.execute();

        expect(createAnnotation).toHaveBeenCalledWith({
            parent_sample_id: 'sample-456',
            annotation_type: 'instance_segmentation',
            annotation_label_id: 'label-id-car',
            x: 15,
            y: 25,
            width: 200,
            height: 150,
            segmentation_mask: [1, 2, 3, 4, 5]
        });
        expect(refetch).toHaveBeenCalled();
    });
});
