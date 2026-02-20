import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { applySegmentationMaskConstraints } from './applySegmentationMaskConstraints';

vi.mock('$lib/components/SampleAnnotation/utils', () => ({
    decodeRLEToBinaryMask: vi.fn((mask: number[], width: number, height: number) =>
        Uint8Array.from(mask).slice(0, width * height)
    ),
    encodeBinaryMaskToRLE: vi.fn((mask: Uint8Array) => Array.from(mask)),
    computeBoundingBoxFromMask: vi.fn(() => ({ x: 0, y: 0, width: 1, height: 1 }))
}));

const sample = { width: 4, height: 4 };
const baseAnn = (id: string, mask: number[]): AnnotationView =>
    ({
        sample_id: id,
        annotation_type: 'semantic_segmentation',
        segmentation_details: { segmentation_mask: mask },
        annotation_label: { annotation_label_name: 'a', annotation_label_id: 'a' },
        parent_sample_id: 'p',
        created_at: '',
        tags: []
    }) as AnnotationView;

describe('applySegmentationMaskConstraints', () => {
    const updateAnnotations = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('strips locked pixels and updates overlaps in one call', async () => {
        const workingMask = Uint8Array.from([1, 1, 0, 0]);
        const locked = new Set(['lock']);
        const annotations = [baseAnn('lock', [1, 1, 0, 0]), baseAnn('other', [1, 0, 0, 0])];

        await applySegmentationMaskConstraints({
            workingMask,
            lockedAnnotationIds: locked,
            annotations,
            segmentationMode: 'semantic',
            sample,
            skipId: 'new',
            collectionId: 'c',
            updateAnnotations
        });

        // Locked mask should clear the drawn pixels in-place.
        expect(Array.from(workingMask)).toEqual([0, 0, 0, 0]);
        // Overlap with "other" should trigger an update call.
        expect(updateAnnotations).toHaveBeenCalledTimes(1);
    });
});
