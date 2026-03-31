import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { removeOverlapFromOtherSegmentationAnnotations } from './removeOverlapFromOtherSegmentationAnnotations';

vi.mock('$lib/components/SampleAnnotation/utils', () => ({
    decodeRLEToBinaryMask: vi.fn((mask: number[], width: number, height: number) =>
        Uint8Array.from(mask).slice(0, width * height)
    ),
    encodeBinaryMaskToRLE: vi.fn((mask: Uint8Array) => Array.from(mask)),
    computeBoundingBoxFromMask: vi.fn(() => ({ x: 0, y: 0, width: 1, height: 1 }))
}));

const sample = { width: 4, height: 4 };
const baseAnn = (
    id: string,
    mask: number[],
    annotationType: 'instance_segmentation' | 'semantic_segmentation' = 'instance_segmentation'
): AnnotationView =>
    ({
        sample_id: id,
        annotation_type: annotationType,
        segmentation_details: { segmentation_mask: mask },
        annotation_label: { annotation_label_name: 'a', annotation_label_id: 'a' },
        parent_sample_id: 'p',
        created_at: '',
        tags: []
    }) as unknown as AnnotationView;

describe('removeOverlapFromOtherSegmentationAnnotations', () => {
    const updateAnnotations = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('clears overlapping pixels on other instance masks and sends an update', async () => {
        const overriddenAnnotations = await removeOverlapFromOtherSemanticAnnotations({
            newMask: Uint8Array.from([1, 0, 0, 0]),
            annotations: [baseAnn('1', [1, 1, 0, 0])],
            segmentationMode: 'instance',
            sample,
            collectionId: 'c',
            updateAnnotations
        });

        // In instance mode, one-pixel ownership is enforced across instance masks.
        expect(updateAnnotations).toHaveBeenCalledTimes(1);
        const [updates] = updateAnnotations.mock.calls[0];
        expect(updates[0].annotation_id).toBe('1');
        expect(overriddenAnnotations.map((annotation) => annotation.sample_id)).toEqual(['1']);
    });

    it('respects locked annotations and leaves them untouched', async () => {
        const overriddenAnnotations = await removeOverlapFromOtherSemanticAnnotations({
            newMask: Uint8Array.from([1, 0, 0, 0]),
            annotations: [baseAnn('1', [1, 0, 0, 0])],
            segmentationMode: 'instance',
            sample,
            collectionId: 'c',
            lockedAnnotationIds: new Set(['1']),
            updateAnnotations
        });

        // Locked annotations should never be updated even if they overlap.
        expect(updateAnnotations).not.toHaveBeenCalled();
        expect(overriddenAnnotations).toEqual([]);
    });

    it('clears overlapping pixels on other semantic masks and sends an update in semantic mode', async () => {
        const overriddenAnnotations = await removeOverlapFromOtherSemanticAnnotations({
            newMask: Uint8Array.from([1, 0, 0, 0]),
            annotations: [baseAnn('1', [1, 1, 0, 0], 'semantic_segmentation')],
            segmentationMode: 'semantic',
            sample,
            collectionId: 'c',
            updateAnnotations
        });

        // Only one annotation overlaps; expect a single update payload.
        expect(updateAnnotations).toHaveBeenCalledTimes(1);
        const [updates] = updateAnnotations.mock.calls[0];
        expect(updates[0].annotation_id).toBe('1');
        expect(overriddenAnnotations.map((annotation) => annotation.sample_id)).toEqual(['1']);
    });
});
