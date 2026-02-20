import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';

import { useInstanceSegmentationBrush } from './useInstanceSegmentationBrush';
import {
    computeBoundingBoxFromMask,
    encodeBinaryMaskToRLE
} from '$lib/components/SampleAnnotation/utils';
import { toast } from 'svelte-sonner';

const annotationLabelContext = {
    isDrawing: true,
    annotationId: null as string | null,
    annotationLabel: null as string | null,
    lastCreatedAnnotationId: null as string | null
};

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({
        context: annotationLabelContext,
        setAnnotationId(id: string | null) {
            annotationLabelContext.annotationId = id;
        },

        setAnnotationLabel(label: string | null) {
            annotationLabelContext.annotationLabel = label;
        },
        setLastCreatedAnnotationId(id: string | null) {
            annotationLabelContext.lastCreatedAnnotationId = id;
        },
        setIsDrawing(value: boolean) {
            annotationLabelContext.isDrawing = value;
        }
    })
}));

vi.mock('$lib/components/SampleAnnotation/utils', () => ({
    computeBoundingBoxFromMask: vi.fn(),
    encodeBinaryMaskToRLE: vi.fn(),
    getBoundingBox: vi.fn()
}));

const createAnnotation = vi.fn();
const createLabel = vi.fn();
const deleteAnnotation = vi.fn();

vi.mock('$lib/hooks/useCreateAnnotation/useCreateAnnotation', () => ({
    useCreateAnnotation: () => ({ createAnnotation })
}));

vi.mock('$lib/hooks/useDeleteAnnotation/useDeleteAnnotation', () => ({
    useDeleteAnnotation: () => ({ deleteAnnotation })
}));

vi.mock('$lib/hooks/useCreateLabel/useCreateLabel', () => ({
    useCreateLabel: () => ({ createLabel })
}));

vi.mock('svelte-sonner', () => {
    return {
        toast: {
            error: vi.fn()
        }
    };
});

const bbox = { x: 1, y: 2, width: 10, height: 20 };
const rle = [1, 2, 3];
const mask = new Uint8Array(100);

const sample = { width: 100, height: 100 };

describe('useInstanceSegmentationBrush', () => {
    beforeEach(() => {
        annotationLabelContext.isDrawing = true;
        annotationLabelContext.annotationId = null;
        annotationLabelContext.annotationLabel = null;
        annotationLabelContext.lastCreatedAnnotationId = null;

        vi.clearAllMocks();

        computeBoundingBoxFromMask.mockReturnValue(bbox);
        encodeBinaryMaskToRLE.mockReturnValue(rle);

        createAnnotation.mockResolvedValue({
            sample_id: 'new-annotation-id'
        });

        createLabel.mockResolvedValue({
            annotation_label_id: 'default-label-id',
            annotation_label_name: 'DEFAULT'
        });
    });

    it('does nothing when not drawing', async () => {
        annotationLabelContext.isDrawing = false;

        const refetch = vi.fn();

        const { finishBrush } = useInstanceSegmentationBrush({
            collectionId: 'c1',
            sampleId: 's1',
            sample,
            refetch
        });

        await finishBrush(mask, null, []);

        expect(createAnnotation).not.toHaveBeenCalled();
        expect(refetch).not.toHaveBeenCalled();
        expect(annotationLabelContext.isDrawing).toBe(false);
    });

    it('shows toast error when bounding box is invalid', async () => {
        computeBoundingBoxFromMask.mockReturnValue(null);

        const refetch = vi.fn();

        const { finishBrush } = useInstanceSegmentationBrush({
            collectionId: 'c1',
            sampleId: 's1',
            sample,
            refetch
        });

        await finishBrush(mask, null, []);

        expect(toast.error).toHaveBeenCalledWith('Invalid segmentation mask');
        expect(createAnnotation).not.toHaveBeenCalled();
        expect(refetch).not.toHaveBeenCalled();
    });

    it('updates an existing annotation when selectedAnnotation is provided', async () => {
        const refetch = vi.fn();
        const updateAnnotation = vi.fn().mockResolvedValue(true);

        annotationLabelContext.annotationId = 'existing-id';

        const selectedAnnotation = {
            sample_id: 'existing-id'
        } as AnnotationView;

        const { finishBrush } = useInstanceSegmentationBrush({
            collectionId: 'c1',
            sampleId: 's1',
            sample,
            refetch
        });

        await finishBrush(mask, selectedAnnotation, [], updateAnnotation);

        expect(updateAnnotation).toHaveBeenCalledWith({
            annotation_id: 'existing-id',
            collection_id: 'c1',
            bounding_box: bbox,
            segmentation_mask: rle
        });

        expect(createAnnotation).not.toHaveBeenCalled();
        expect(refetch).toHaveBeenCalled();
    });

    it('creates a new annotation using an existing label', async () => {
        const refetch = vi.fn();

        annotationLabelContext.annotationLabel = 'car';

        const labels = [
            {
                annotation_label_id: 'car-label-id',
                annotation_label_name: 'car'
            }
        ];

        const { finishBrush } = useInstanceSegmentationBrush({
            collectionId: 'c1',
            sampleId: 's1',
            sample,
            refetch
        });

        await finishBrush(mask, null, labels);

        expect(createAnnotation).toHaveBeenCalledWith(
            expect.objectContaining({
                parent_sample_id: 's1',
                annotation_type: 'instance_segmentation',
                segmentation_mask: rle,
                annotation_label_id: 'car-label-id'
            })
        );

        expect(annotationLabelContext.annotationId).toBe('new-annotation-id');
        expect(annotationLabelContext.lastCreatedAnnotationId).toBe('new-annotation-id');
        expect(refetch).toHaveBeenCalled();
    });

    it('creates default label when no label exists', async () => {
        const refetch = vi.fn();

        const { finishBrush } = useInstanceSegmentationBrush({
            collectionId: 'c1',
            sampleId: 's1',
            sample,
            refetch
        });

        await finishBrush(mask, null, []);

        expect(createLabel).toHaveBeenCalledWith({
            dataset_id: 'c1',
            annotation_label_name: 'DEFAULT'
        });

        expect(createAnnotation).toHaveBeenCalled();
        expect(refetch).toHaveBeenCalled();
    });
});
