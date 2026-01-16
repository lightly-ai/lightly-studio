import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useSegmentationMaskEraser } from './useSegmentationMaskEraser';

import {
    computeBoundingBoxFromMask,
    encodeBinaryMaskToRLE
} from '$lib/components/SampleAnnotation/utils';

const annotationLabelContext = {
    isDrawing: true,
    annotationId: 'annotation-id'
};

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({ context: annotationLabelContext })
}));

vi.mock('$lib/components/SampleAnnotation/utils', () => ({
    computeBoundingBoxFromMask: vi.fn(),
    encodeBinaryMaskToRLE: vi.fn()
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

        annotationLabelContext.isDrawing = false;

        const { finishErase } = useSegmentationMaskEraser({
            collectionId: 'c1',
            sample,
            refetch
        });

        await finishErase(null);

        expect(refetch).not.toHaveBeenCalled();
        expect(annotationLabelContext.isDrawing).toBe(false);
    });

    it('removes annotation when bounding box is invalid', async () => {
        const refetch = vi.fn();
        const remove = vi.fn().mockResolvedValue(undefined);

        computeBoundingBoxFromMask.mockReturnValue(null);

        const { finishErase } = useSegmentationMaskEraser({
            collectionId: 'c1',
            sample,
            refetch
        });

        await finishErase(mask, undefined, remove);

        expect(remove).toHaveBeenCalled();
        expect(refetch).toHaveBeenCalled();
    });

    it('updates annotation when bounding box is valid', async () => {
        const refetch = vi.fn();
        const update = vi.fn().mockResolvedValue(undefined);

        computeBoundingBoxFromMask.mockReturnValue(bbox);
        encodeBinaryMaskToRLE.mockReturnValue(rle);

        const { finishErase } = useSegmentationMaskEraser({
            collectionId: 'c1',
            sample,
            refetch
        });

        await finishErase(mask, update);

        expect(update).toHaveBeenCalledWith({
            annotation_id: 'annotation-id',
            collection_id: 'c1',
            bounding_box: bbox,
            segmentation_mask: rle
        });

        expect(refetch).toHaveBeenCalled();
    });
});
