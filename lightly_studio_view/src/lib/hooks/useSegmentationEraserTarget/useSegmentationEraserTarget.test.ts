import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { encodeBinaryMaskToRLE } from '$lib/components/SampleAnnotation/utils';
import { useSegmentationEraserTarget } from './useSegmentationEraserTarget';

const { mockContext, lockedAnnotationIds, selectAnnotationMock } = vi.hoisted(() => {
    const lockedIds = new Set<string>();
    const context = {
        annotationId: null as string | null
    };
    const selectAnnotation = vi.fn(({ annotationId }: { annotationId: string }) => {
        context.annotationId = annotationId;
    });

    return {
        mockContext: context,
        lockedAnnotationIds: lockedIds,
        selectAnnotationMock: selectAnnotation
    };
});

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({
        context: mockContext,
        isAnnotationLocked: (annotationId?: string | null) =>
            annotationId ? lockedAnnotationIds.has(annotationId) : false
    })
}));

vi.mock('$lib/hooks/useAnnotationSelection/useAnnotationSelection', () => ({
    useAnnotationSelection: () => ({
        selectAnnotation: selectAnnotationMock
    })
}));

function createMask({
    width,
    height,
    activeIndexes
}: {
    width: number;
    height: number;
    activeIndexes: number[];
}) {
    const mask = new Uint8Array(width * height);
    for (const idx of activeIndexes) {
        mask[idx] = 1;
    }

    return encodeBinaryMaskToRLE(mask);
}

function createAnnotation({
    id,
    segmentationMask,
    width,
    height
}: {
    id: string;
    segmentationMask: number[];
    width: number;
    height: number;
}) {
    return {
        sample_id: id,
        annotation_type: 'instance_segmentation',
        annotation_label: { annotation_label_name: 'Car' },
        segmentation_details: {
            x: 0,
            y: 0,
            width,
            height,
            segmentation_mask: segmentationMask
        }
    } as AnnotationView;
}

describe('useSegmentationEraserTarget', () => {
    const width = 4;
    const height = 4;
    const pointOnIndexFive = { x: 1, y: 1 };

    beforeEach(() => {
        vi.clearAllMocks();
        mockContext.annotationId = null;
        lockedAnnotationIds.clear();
    });

    it('returns not_found when no annotation mask contains the point', () => {
        const annotation = createAnnotation({
            id: 'ann-1',
            segmentationMask: createMask({
                width,
                height,
                activeIndexes: [0]
            }),
            width,
            height
        });

        const { resolveTargetAtPoint } = useSegmentationEraserTarget({
            sample: { width, height, annotations: [annotation] },
            collectionId: 'collection-1'
        });

        const result = resolveTargetAtPoint(pointOnIndexFive);

        expect(result.error).toBe('not_found');
        expect(result.annotation).toBeNull();
        expect(result.workingMask).toBeNull();
        expect(selectAnnotationMock).not.toHaveBeenCalled();
    });

    it('returns locked when the target annotation is locked', () => {
        const annotation = createAnnotation({
            id: 'ann-1',
            segmentationMask: createMask({
                width,
                height,
                activeIndexes: [5]
            }),
            width,
            height
        });
        lockedAnnotationIds.add('ann-1');

        const { resolveTargetAtPoint } = useSegmentationEraserTarget({
            sample: { width, height, annotations: [annotation] },
            collectionId: 'collection-1'
        });

        const result = resolveTargetAtPoint(pointOnIndexFive);

        expect(result.error).toBe('locked');
        expect(result.annotation).toBeNull();
        expect(result.workingMask).toBeNull();
        expect(selectAnnotationMock).not.toHaveBeenCalled();
    });

    it('auto-selects and returns working mask when target is unlocked', () => {
        const annotation = createAnnotation({
            id: 'ann-1',
            segmentationMask: createMask({
                width,
                height,
                activeIndexes: [5]
            }),
            width,
            height
        });

        const { resolveTargetAtPoint } = useSegmentationEraserTarget({
            sample: { width, height, annotations: [annotation] },
            collectionId: 'collection-1'
        });

        const result = resolveTargetAtPoint(pointOnIndexFive);

        expect(result.error).toBeUndefined();
        expect(result.annotation?.sample_id).toBe('ann-1');
        expect(result.workingMask?.[5]).toBe(1);
        expect(selectAnnotationMock).toHaveBeenCalledWith({
            annotationId: 'ann-1',
            annotations: [annotation],
            collectionId: 'collection-1'
        });
    });

    it('prefers the top-most annotation on overlapping masks', () => {
        const bottom = createAnnotation({
            id: 'ann-bottom',
            segmentationMask: createMask({
                width,
                height,
                activeIndexes: [5]
            }),
            width,
            height
        });
        const top = createAnnotation({
            id: 'ann-top',
            segmentationMask: createMask({
                width,
                height,
                activeIndexes: [5]
            }),
            width,
            height
        });

        const { resolveTargetAtPoint } = useSegmentationEraserTarget({
            sample: { width, height, annotations: [bottom, top] },
            collectionId: 'collection-1'
        });

        const result = resolveTargetAtPoint(pointOnIndexFive);

        expect(result.annotation?.sample_id).toBe('ann-top');
        expect(selectAnnotationMock).toHaveBeenCalledWith({
            annotationId: 'ann-top',
            annotations: [bottom, top],
            collectionId: 'collection-1'
        });
    });

    it('does not re-select when the target annotation is already selected', () => {
        const annotation = createAnnotation({
            id: 'ann-1',
            segmentationMask: createMask({
                width,
                height,
                activeIndexes: [5]
            }),
            width,
            height
        });
        mockContext.annotationId = 'ann-1';

        const { resolveTargetAtPoint } = useSegmentationEraserTarget({
            sample: { width, height, annotations: [annotation] },
            collectionId: 'collection-1'
        });

        const result = resolveTargetAtPoint(pointOnIndexFive);

        expect(result.annotation?.sample_id).toBe('ann-1');
        expect(result.error).toBeUndefined();
        expect(selectAnnotationMock).not.toHaveBeenCalled();
    });
});
