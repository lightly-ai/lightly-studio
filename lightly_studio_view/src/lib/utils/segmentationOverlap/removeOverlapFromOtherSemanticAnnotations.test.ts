import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { removeOverlapFromOtherSemanticAnnotations } from './removeOverlapFromOtherSemanticAnnotations';

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

describe('removeOverlapFromOtherSemanticAnnotations', () => {
    const updateAnnotations = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('skips overlap removal when mode is instance segmentation', async () => {
        await removeOverlapFromOtherSemanticAnnotations({
            newMask: new Uint8Array(16),
            annotations: [baseAnn('1', [1, 1, 0, 0])],
            segmentationMode: 'instance',
            sample,
            collectionId: 'c',
            updateAnnotations
        });

        // In instance mode, we should not alter other semantic masks.
        expect(updateAnnotations).not.toHaveBeenCalled();
    });

    it('respects locked annotations and leaves them untouched', async () => {
        await removeOverlapFromOtherSemanticAnnotations({
            newMask: Uint8Array.from([1, 0, 0, 0]),
            annotations: [baseAnn('1', [1, 0, 0, 0])],
            segmentationMode: 'semantic',
            sample,
            collectionId: 'c',
            lockedAnnotationIds: new Set(['1']),
            updateAnnotations
        });

        // Locked annotations should never be updated even if they overlap.
        expect(updateAnnotations).not.toHaveBeenCalled();
    });

    it('clears overlapping pixels on other semantic masks and sends an update', async () => {
        await removeOverlapFromOtherSemanticAnnotations({
            newMask: Uint8Array.from([1, 0, 0, 0]),
            annotations: [baseAnn('1', [1, 1, 0, 0])],
            segmentationMode: 'semantic',
            sample,
            collectionId: 'c',
            updateAnnotations
        });

        // Only one annotation overlaps; expect a single update payload.
        expect(updateAnnotations).toHaveBeenCalledTimes(1);
        const [updates] = updateAnnotations.mock.calls[0];
        expect(updates[0].annotation_id).toBe('1');
    });
});
