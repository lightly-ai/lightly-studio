import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { restoreOverriddenSegmentationAnnotationsForUndo } from './restoreOverriddenSegmentationAnnotationsForUndo';

vi.mock('$lib/components/SampleAnnotation/utils', () => ({
    getBoundingBox: vi.fn(() => ({ x: 3, y: 4, width: 5, height: 6 }))
}));

const baseAnnotation = (id: string): AnnotationView =>
    ({
        sample_id: id,
        parent_sample_id: 'parent-sample-id',
        annotation_type: 'segmentation_mask',
        annotation_label: {
            annotation_label_name: 'car'
        },
        segmentation_details: {
            x: 3,
            y: 4,
            width: 5,
            height: 6,
            segmentation_mask: [1, 0, 2]
        },
        created_at: new Date(),
        tags: []
    }) as AnnotationView;

describe('restoreOverriddenSegmentationAnnotationsForUndo', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('restores overridden annotations through update', async () => {
        const updateAnnotations = vi.fn().mockResolvedValue(undefined);
        const createAnnotation = vi.fn().mockResolvedValue(undefined);

        await restoreOverriddenSegmentationAnnotationsForUndo({
            collectionId: 'collection-id',
            overriddenAnnotations: [baseAnnotation('annotation-1')],
            labels: [
                {
                    annotation_label_id: 'label-car',
                    annotation_label_name: 'car'
                }
            ],
            updateAnnotations,
            createAnnotation
        });

        expect(updateAnnotations).toHaveBeenCalledWith([
            {
                annotation_id: 'annotation-1',
                collection_id: 'collection-id',
                bounding_box: { x: 3, y: 4, width: 5, height: 6 },
                segmentation_mask: [1, 0, 2]
            }
        ]);
        expect(createAnnotation).not.toHaveBeenCalled();
    });

    it('recreates an annotation when update reports it as missing', async () => {
        const updateAnnotations = vi.fn().mockRejectedValue({ status: 404 });
        const createAnnotation = vi.fn().mockResolvedValue(undefined);

        await restoreOverriddenSegmentationAnnotationsForUndo({
            collectionId: 'collection-id',
            overriddenAnnotations: [baseAnnotation('annotation-1')],
            labels: [
                {
                    annotation_label_id: 'label-car',
                    annotation_label_name: 'car'
                }
            ],
            updateAnnotations,
            createAnnotation
        });

        expect(updateAnnotations).toHaveBeenCalledTimes(1);
        expect(createAnnotation).toHaveBeenCalledWith({
            parent_sample_id: 'parent-sample-id',
            annotation_type: 'segmentation_mask',
            annotation_label_id: 'label-car',
            x: 3,
            y: 4,
            width: 5,
            height: 6,
            segmentation_mask: [1, 0, 2]
        });
    });

    it('throws when update fails with a non-not-found error', async () => {
        const updateAnnotations = vi.fn().mockRejectedValue(new Error('Failed to restore'));
        const createAnnotation = vi.fn().mockResolvedValue(undefined);

        await expect(
            restoreOverriddenSegmentationAnnotationsForUndo({
                collectionId: 'collection-id',
                overriddenAnnotations: [baseAnnotation('annotation-1')],
                labels: [],
                updateAnnotations,
                createAnnotation
            })
        ).rejects.toThrow('Failed to restore');

        expect(createAnnotation).not.toHaveBeenCalled();
    });

    it('skips recreation when no label id can be resolved', async () => {
        const updateAnnotations = vi.fn().mockRejectedValue({ status: 404 });
        const createAnnotation = vi.fn().mockResolvedValue(undefined);
        const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined);

        await restoreOverriddenSegmentationAnnotationsForUndo({
            collectionId: 'collection-id',
            overriddenAnnotations: [baseAnnotation('annotation-1')],
            labels: [],
            updateAnnotations,
            createAnnotation
        });

        expect(createAnnotation).not.toHaveBeenCalled();
        expect(consoleErrorSpy).toHaveBeenCalledWith(
            'Cannot restore annotation "annotation-1" because no label id was found.'
        );
    });
});
