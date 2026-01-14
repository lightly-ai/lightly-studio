import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useSegmentationMaskEraser } from './useSegmentationMaskEraser';
import type { AnnotationView } from '$lib/api/lightly_studio_local';

import {
    computeBoundingBoxFromMask,
    encodeBinaryMaskToRLE
} from '$lib/components/SampleAnnotation/utils';

const annotationLabelContext = {
    isDrawing: true,
    annotationId: 'annotation-id'
};

const deleteAnnotation = vi.fn();

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => annotationLabelContext
}));

vi.mock('$lib/components/SampleAnnotation/utils', () => ({
    computeBoundingBoxFromMask: vi.fn(),
    encodeBinaryMaskToRLE: vi.fn(),
    getBoundingBox: vi.fn()
}));

vi.mock('$lib/hooks/useDeleteAnnotation/useDeleteAnnotation', () => ({
    useDeleteAnnotation: () => ({ deleteAnnotation })
}));

vi.mock('svelte-sonner', () => ({
    toast: {
        error: vi.fn()
    }
}));

const sample = { width: 100, height: 100 };
const mask = new Uint8Array(10);
const bbox = { x: 1, y: 2, width: 10, height: 20 };
const rle = [1, 2, 3];

describe('useSegmentationMaskEraser', () => {
    beforeEach(() => {
        annotationLabelContext.isDrawing = true;

        vi.clearAllMocks();

        computeBoundingBoxFromMask.mockReturnValue(bbox);
        encodeBinaryMaskToRLE.mockReturnValue(rle);
    });

    it('resets drawing state and returns when not drawing or mask is null', async () => {
        const refetch = vi.fn();
        const selectedAnnotation = {
            sample_id: 'existing-id'
        } as AnnotationView;
        annotationLabelContext.isDrawing = false;

        const { finishErase } = useSegmentationMaskEraser({
            collectionId: 'c1',
            sample,
            refetch
        });

        await finishErase(null, selectedAnnotation);

        expect(refetch).not.toHaveBeenCalled();
        expect(annotationLabelContext.isDrawing).toBe(false);
    });

    it('removes annotation when bounding box is invalid', async () => {
        const refetch = vi.fn();
        const remove = vi.fn().mockResolvedValue(undefined);
        const selectedAnnotation = {
            sample_id: 'existing-id'
        } as AnnotationView;
        computeBoundingBoxFromMask.mockReturnValue(null);

        const { finishErase } = useSegmentationMaskEraser({
            collectionId: 'c1',
            sample,
            refetch
        });

        await finishErase(mask, selectedAnnotation, undefined, remove);

        expect(remove).toHaveBeenCalled();
        expect(refetch).toHaveBeenCalled();
    });

    it('updates annotation when bounding box is valid', async () => {
        const refetch = vi.fn();
        const update = vi.fn().mockResolvedValue(undefined);

        const selectedAnnotation = {
            sample_id: 'existing-id'
        } as AnnotationView;

        computeBoundingBoxFromMask.mockReturnValue(bbox);
        encodeBinaryMaskToRLE.mockReturnValue(rle);

        const { finishErase } = useSegmentationMaskEraser({
            collectionId: 'c1',
            sample,
            refetch
        });

        await finishErase(mask, selectedAnnotation, update);

        expect(update).toHaveBeenCalledWith({
            annotation_id: 'existing-id',
            collection_id: 'c1',
            bounding_box: bbox,
            segmentation_mask: rle
        });

        expect(refetch).toHaveBeenCalled();
    });
});
