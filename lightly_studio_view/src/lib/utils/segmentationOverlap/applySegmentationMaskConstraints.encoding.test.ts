import { describe, it, expect, vi } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import {
    decodeRLEToBinaryMask,
    encodeBinaryMaskToRLE
} from '$lib/components/SampleAnnotation/utils';
import { applySegmentationMaskConstraints } from './applySegmentationMaskConstraints';

// Uses the real mask encoding and bounding box calculation.
const sample = { width: 3, height: 2 };
const annotation = (id: string, mask: number[]): AnnotationView =>
    ({
        sample_id: id,
        annotation_type: 'segmentation_mask',
        segmentation_details: { segmentation_mask: encodeBinaryMaskToRLE(Uint8Array.from(mask)) }
    }) as unknown as AnnotationView;

describe('applySegmentationMaskConstraints with real mask encoding', () => {
    it('trims other masks only with the pixels left after locked pixels are removed', async () => {
        const updateAnnotations = vi.fn();
        // The stroke covers the top row. The locked mask covers its first two pixels.
        const workingMask = Uint8Array.from([1, 1, 1, 0, 0, 0]);
        const annotations = [
            annotation('lock', [1, 1, 0, 0, 0, 0]),
            annotation('other', [0, 1, 1, 0, 1, 1])
        ];

        await applySegmentationMaskConstraints({
            workingMask,
            lockedAnnotationIds: new Set(['lock']),
            annotations,
            sample,
            skipId: 'new',
            collectionId: 'c',
            updateAnnotations
        });

        expect(Array.from(workingMask)).toEqual([0, 0, 1, 0, 0, 0]);
        expect(updateAnnotations).toHaveBeenCalledTimes(1);
        const [[update]] = updateAnnotations.mock.calls[0];
        expect(update.annotation_id).toBe('other');
        expect(Array.from(decodeRLEToBinaryMask(update.segmentation_mask, 3, 2))).toEqual([
            0, 1, 0, 0, 1, 1
        ]);
        expect(update.bounding_box).toEqual({ x: 1, y: 0, width: 2, height: 2 });
    });
});
