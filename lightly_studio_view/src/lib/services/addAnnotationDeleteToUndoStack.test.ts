import { describe, it, expect, vi } from 'vitest';
import { addAnnotationDeleteToUndoStack } from './addAnnotationDeleteToUndoStack';
import type {
    AnnotationCollectionView,
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
        annotation_collection_id: 'source-collection-abc',
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

    const mockSources: AnnotationCollectionView[] = [
        {
            collection_id: 'source-collection-abc',
            name: 'my-model-predictions'
        } as AnnotationCollectionView,
        {
            collection_id: 'source-collection-other',
            name: 'ground-truth'
        } as AnnotationCollectionView
    ];

    it('should add a reversible action to undo stack', () => {
        const addReversibleAction = vi.fn();
        const createAnnotation = vi.fn().mockResolvedValue({} as CreateAnnotationResponse);
        const refetch = vi.fn();

        addAnnotationDeleteToUndoStack({
            annotation: mockAnnotation,
            labels: mockLabels,
            sources: mockSources,
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
            sources: mockSources,
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
            annotation_collection_name: 'my-model-predictions',
            x: 10,
            y: 20,
            width: 100,
            height: 50,
            segmentation_mask: undefined
        });
        expect(refetch).toHaveBeenCalled();
    });

    it('restores a deleted polygon with its vertices', async () => {
        const addReversibleAction = vi.fn();
        const createAnnotation = vi.fn().mockResolvedValue({} as CreateAnnotationResponse);
        const polygons = [
            [
                [0, 0],
                [10, 0],
                [10, 10]
            ]
        ];

        addAnnotationDeleteToUndoStack({
            annotation: {
                ...mockAnnotation,
                annotation_type: 'polygon',
                object_detection_details: undefined,
                polygon_details: { x: 0, y: 0, width: 10, height: 10, polygons }
            },
            labels: mockLabels,
            sources: mockSources,
            addReversibleAction,
            createAnnotation,
            refetch: vi.fn()
        });
        await (addReversibleAction.mock.calls[0][0] as ReversibleAction).execute();

        expect(createAnnotation).toHaveBeenCalledWith(
            expect.objectContaining({ annotation_type: 'polygon', polygons })
        );
    });

    const executeUndo = async (refetch: () => unknown) => {
        const addReversibleAction = vi.fn();
        addAnnotationDeleteToUndoStack({
            annotation: mockAnnotation,
            labels: mockLabels,
            sources: mockSources,
            addReversibleAction,
            createAnnotation: vi.fn().mockResolvedValue({} as CreateAnnotationResponse),
            refetch
        });
        return (addReversibleAction.mock.calls[0][0] as ReversibleAction).execute();
    };

    it('completes the undo only after the refetch is complete', async () => {
        let finishRefetch!: () => void;
        let isComplete = false;

        const undo = executeUndo(
            () => new Promise<void>((resolve) => (finishRefetch = resolve))
        ).then(() => (isComplete = true));
        await vi.waitFor(() => expect(finishRefetch).toBeDefined());
        expect(isComplete).toBe(false);
        finishRefetch();
        await undo;

        expect(isComplete).toBe(true);
    });

    it('completes the undo when the refetch fails', async () => {
        await expect(
            executeUndo(() => Promise.reject(new Error('refetch failed')))
        ).resolves.toBeUndefined();
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
            sources: mockSources,
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
            sources: mockSources,
            addReversibleAction,
            createAnnotation,
            refetch
        });

        expect(addReversibleAction).not.toHaveBeenCalled();
    });

    it('should handle segmentation mask annotations', async () => {
        const addReversibleAction = vi.fn();
        const createAnnotation = vi.fn().mockResolvedValue({} as CreateAnnotationResponse);
        const refetch = vi.fn();

        const segmentationAnnotation: AnnotationView = {
            ...mockAnnotation,
            annotation_type: 'segmentation_mask',
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
            sources: mockSources,
            addReversibleAction,
            createAnnotation,
            refetch
        });

        const action = addReversibleAction.mock.calls[0][0] as ReversibleAction;
        await action.execute();

        expect(createAnnotation).toHaveBeenCalledWith({
            parent_sample_id: 'sample-456',
            annotation_type: 'segmentation_mask',
            annotation_label_id: 'label-id-car',
            annotation_collection_name: 'my-model-predictions',
            x: 15,
            y: 25,
            width: 200,
            height: 150,
            segmentation_mask: [1, 2, 3, 4, 5]
        });
        expect(refetch).toHaveBeenCalled();
    });

    describe('cuboid annotations', () => {
        const cuboidDetails = {
            frame_id: 'lidar-top',
            px: 1,
            py: 2,
            pz: 3,
            qx: 0,
            qy: 0,
            qz: 0.6,
            qw: 0.8,
            sx: 4,
            sy: 5,
            sz: 6,
            interpolated: true
        };
        const cuboidAnnotation: AnnotationView = {
            ...mockAnnotation,
            annotation_type: 'cuboid_3d',
            object_detection_details: undefined,
            cuboid_3d_details: cuboidDetails,
            object_track_id: 'track-1'
        };

        const undoDelete = async (
            annotation: AnnotationView,
            onRestored?: (restored: AnnotationView) => void
        ) => {
            const addReversibleAction = vi.fn();
            const createAnnotation = vi
                .fn()
                .mockResolvedValue({ sample_id: 'restored-1' } as CreateAnnotationResponse);
            addAnnotationDeleteToUndoStack({
                annotation,
                labels: mockLabels,
                sources: mockSources,
                addReversibleAction,
                createAnnotation,
                refetch: vi.fn(),
                onRestored
            });
            await (addReversibleAction.mock.calls[0][0] as ReversibleAction).execute();
            return createAnnotation;
        };

        it('restores a cuboid with its geometry, interpolation and track', async () => {
            const createAnnotation = await undoDelete(cuboidAnnotation);

            expect(createAnnotation).toHaveBeenCalledWith(
                expect.objectContaining({
                    annotation_type: 'cuboid_3d',
                    annotation_label_id: 'label-id-car',
                    annotation_collection_name: 'my-model-predictions',
                    cuboid_3d: cuboidDetails,
                    object_track_id: 'track-1'
                })
            );
        });

        it('restores an untracked cuboid without a track', async () => {
            const createAnnotation = await undoDelete({
                ...cuboidAnnotation,
                object_track_id: null
            });

            expect(createAnnotation).toHaveBeenCalledWith(
                expect.objectContaining({ cuboid_3d: cuboidDetails, object_track_id: null })
            );
        });

        it('passes the restored annotation to onRestored', async () => {
            const onRestored = vi.fn();

            await undoDelete(cuboidAnnotation, onRestored);

            expect(onRestored).toHaveBeenCalledWith({ sample_id: 'restored-1' });
        });
    });
});
