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
        annotation_type: 'segmentation_mask',
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

    it('strips locked pixels and trims overlaps only with the remaining pixels', async () => {
        const workingMask = Uint8Array.from([1, 1, 1, 0]);
        const locked = new Set(['lock']);
        const annotations = [baseAnn('lock', [1, 1, 0, 0]), baseAnn('other', [1, 0, 1, 0])];

        const overriddenAnnotations = await applySegmentationMaskConstraints({
            workingMask,
            lockedAnnotationIds: locked,
            annotations,
            sample,
            skipId: 'new',
            collectionId: 'c',
            updateAnnotations
        });

        // Locked mask should clear the locked drawn pixels in-place.
        expect(Array.from(workingMask)).toEqual([0, 0, 1, 0]);
        // Pixels rejected by the lock do not trim "other".
        expect(updateAnnotations).toHaveBeenCalledTimes(1);
        expect(updateAnnotations).toHaveBeenCalledWith([
            expect.objectContaining({ annotation_id: 'other', segmentation_mask: [1, 0, 0, 0] })
        ]);
        expect(overriddenAnnotations.map((annotation) => annotation.sample_id)).toEqual(['other']);
    });

    it('does not trim other masks when locked masks cover the whole stroke', async () => {
        const workingMask = Uint8Array.from([1, 1, 0, 0]);
        const locked = new Set(['lock']);
        const annotations = [baseAnn('lock', [1, 1, 0, 0]), baseAnn('other', [1, 0, 0, 0])];

        const overriddenAnnotations = await applySegmentationMaskConstraints({
            workingMask,
            lockedAnnotationIds: locked,
            annotations,
            sample,
            skipId: 'new',
            collectionId: 'c',
            updateAnnotations
        });

        expect(Array.from(workingMask)).toEqual([0, 0, 0, 0]);
        expect(updateAnnotations).not.toHaveBeenCalled();
        expect(overriddenAnnotations).toEqual([]);
    });

    it('does not trim other masks when painting onto an existing mask fully over a locked mask', async () => {
        // "selected" already has pixel 3. The stroke covers pixels 0 and 1, which are locked.
        const workingMask = Uint8Array.from([1, 1, 0, 1]);
        const annotations = [
            baseAnn('selected', [0, 0, 0, 1]),
            baseAnn('lock', [1, 1, 0, 0]),
            baseAnn('other', [1, 0, 0, 0])
        ];

        const overriddenAnnotations = await applySegmentationMaskConstraints({
            workingMask,
            lockedAnnotationIds: new Set(['lock']),
            annotations,
            sample,
            skipId: 'selected',
            collectionId: 'c',
            updateAnnotations
        });

        expect(Array.from(workingMask)).toEqual([0, 0, 0, 1]);
        expect(updateAnnotations).not.toHaveBeenCalled();
        expect(overriddenAnnotations).toEqual([]);
    });

    it('removes existing pixels of the edited mask that lie on a locked mask', async () => {
        // "selected" already has pixels 0 and 3, and pixel 0 overlaps the locked mask.
        const workingMask = Uint8Array.from([1, 0, 1, 1]);
        const annotations = [baseAnn('selected', [1, 0, 0, 1]), baseAnn('lock', [1, 0, 0, 0])];

        await applySegmentationMaskConstraints({
            workingMask,
            lockedAnnotationIds: new Set(['lock']),
            annotations,
            sample,
            skipId: 'selected',
            collectionId: 'c',
            updateAnnotations
        });

        expect(Array.from(workingMask)).toEqual([0, 0, 1, 1]);
    });

    it('does not trim other masks under pixels erased from the edited mask', async () => {
        // Smart select in erase mode removed pixel 1 from "selected".
        const workingMask = Uint8Array.from([1, 0, 0, 0]);
        const annotations = [baseAnn('selected', [1, 1, 0, 0]), baseAnn('other', [0, 1, 0, 0])];

        const overriddenAnnotations = await applySegmentationMaskConstraints({
            workingMask,
            lockedAnnotationIds: new Set(),
            annotations,
            sample,
            skipId: 'selected',
            collectionId: 'c',
            updateAnnotations
        });

        expect(updateAnnotations).not.toHaveBeenCalled();
        expect(overriddenAnnotations).toEqual([]);
    });
});
