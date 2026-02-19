import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import {
    removeOverlapFromOtherSemanticAnnotations,
    stripLockedPixels,
    applySegmentationMaskConstraints
} from './segmentationOverlap';

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
    }) as unknown as AnnotationView;

describe('segmentationOverlap utils', () => {
    const updateAnnotations = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('removeOverlapFromOtherSemanticAnnotations: skips when not semantic', async () => {
        await removeOverlapFromOtherSemanticAnnotations({
            newMask: new Uint8Array(16),
            annotations: [baseAnn('1', [1, 1, 0, 0])],
            segmentationMode: 'instance',
            sample,
            collectionId: 'c',
            updateAnnotations
        });
        expect(updateAnnotations).not.toHaveBeenCalled();
    });

    it('removeOverlapFromOtherSemanticAnnotations: respects locked annotations', async () => {
        await removeOverlapFromOtherSemanticAnnotations({
            newMask: Uint8Array.from([1, 0, 0, 0]),
            annotations: [baseAnn('1', [1, 0, 0, 0])],
            segmentationMode: 'semantic',
            sample,
            collectionId: 'c',
            lockedAnnotationIds: new Set(['1']),
            updateAnnotations
        });
        expect(updateAnnotations).not.toHaveBeenCalled();
    });

    it('removeOverlapFromOtherSemanticAnnotations: trims overlap and updates', async () => {
        await removeOverlapFromOtherSemanticAnnotations({
            newMask: Uint8Array.from([1, 0, 0, 0]),
            annotations: [baseAnn('1', [1, 1, 0, 0])],
            segmentationMode: 'semantic',
            sample,
            collectionId: 'c',
            updateAnnotations
        });
        expect(updateAnnotations).toHaveBeenCalledTimes(1);
        const callArg = updateAnnotations.mock.calls[0][0][0];
        expect(callArg.annotation_id).toBe('1');
    });

    it('stripLockedPixels: leaves mask untouched when no locks', () => {
        const mask = Uint8Array.from([1, 0, 1, 0]);
        stripLockedPixels({ mask, lockedAnnotationIds: undefined, annotations: [], sample });
        expect(Array.from(mask)).toEqual([1, 0, 1, 0]);
    });

    it('stripLockedPixels: zeroes overlapping pixels from locked masks', () => {
        const mask = Uint8Array.from([1, 1, 0, 0]);
        const locked = new Set(['1']);
        stripLockedPixels({
            mask,
            lockedAnnotationIds: locked,
            annotations: [baseAnn('1', [1, 1, 0, 0])],
            sample
        });
        expect(Array.from(mask)).toEqual([0, 0, 0, 0]);
    });

    it('applySegmentationMaskConstraints: handles lock stripping and overlap updates in one pass', async () => {
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

        expect(Array.from(workingMask)).toEqual([0, 0, 0, 0]);
        expect(updateAnnotations).toHaveBeenCalled();
    });
});
