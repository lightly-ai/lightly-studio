import { fireEvent, render } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SampleEraserRect from './SampleEraserRect/SampleEraserRect.svelte';
import { writable } from 'svelte/store';
import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';

const {
    applyBrushToMaskMock,
    decodeRLEToBinaryMaskMock,
    setAnnotationId,
    setIsDrawing,
    selectAnnotationMock,
    toastErrorMock,
    mockAnnotationContext,
    lockedAnnotationIds
} = vi.hoisted(() => {
    const lockedIds = new Set<string>();
    const context = {
        annotationId: null as string | null,
        isDrawing: false,
        isOnAnnotationDetailsView: false,
        isAnnotationLocked: (annotationId?: string | null) =>
            annotationId ? lockedIds.has(annotationId) : false
    };
    const applyBrush = vi.fn();
    const decodeMask = vi.fn(() => {
        const mask = new Uint8Array(16);
        mask[5] = 1;
        return mask;
    });
    const setAnnotationIdMock = vi.fn((id: string | null) => {
        context.annotationId = id;
    });
    const setIsDrawingMock = vi.fn((value: boolean) => {
        context.isDrawing = value;
    });
    const selectAnnotation = vi.fn(({ annotationId }: { annotationId: string }) => {
        context.annotationId = annotationId;
    });
    const toastError = vi.fn();

    return {
        applyBrushToMaskMock: applyBrush,
        decodeRLEToBinaryMaskMock: decodeMask,
        setAnnotationId: setAnnotationIdMock,
        setIsDrawing: setIsDrawingMock,
        selectAnnotationMock: selectAnnotation,
        toastErrorMock: toastError,
        mockAnnotationContext: context,
        lockedAnnotationIds: lockedIds
    };
});

vi.mock('$app/state', () => ({
    page: {
        params: {
            dataset_id: 'dataset-1',
            collection_type: 'samples'
        },
        data: {
            collectionType: 'samples'
        }
    }
}));

vi.mock('$lib/components/SampleAnnotation/utils', () => ({
    applyBrushToMask: applyBrushToMaskMock,
    decodeRLEToBinaryMask: decodeRLEToBinaryMaskMock,
    getImageCoordsFromMouse: vi.fn(() => ({ x: 1, y: 1 })),
    interpolateLineBetweenPoints: vi.fn(() => []),
    maskToDataUrl: vi.fn(() => 'data:image/png;base64,preview')
}));

vi.mock(
    '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/calculateBinaryMaskFromRLE/parseColor',
    () => ({
        default: vi.fn(() => ({ r: 0, g: 0, b: 255, a: 255 }))
    })
);

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({
        context: mockAnnotationContext,
        setIsDrawing,
        setAnnotationId,
        isAnnotationLocked: (annotationId?: string | null) =>
            annotationId ? lockedAnnotationIds.has(annotationId) : false
    })
}));

vi.mock('$lib/hooks/useAnnotationSelection/useAnnotationSelection', () => ({
    useAnnotationSelection: () => ({
        selectAnnotation: selectAnnotationMock
    })
}));

vi.mock('$lib/hooks/useDeleteAnnotation/useDeleteAnnotation', () => ({
    useDeleteAnnotation: () => ({
        deleteAnnotation: vi.fn()
    })
}));

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () =>
        writable({
            data: []
        })
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        addReversibleAction: vi.fn()
    })
}));

vi.mock('$lib/hooks/useCreateAnnotation/useCreateAnnotation', () => ({
    useCreateAnnotation: () => ({
        createAnnotation: vi.fn()
    })
}));

vi.mock('$lib/hooks/useSegmentationMaskEraser', () => ({
    useSegmentationMaskEraser: () => ({
        finishErase: vi.fn()
    })
}));

vi.mock('$lib/hooks/useAnnotation/useAnnotation', () => ({
    useAnnotation: () => ({
        updateAnnotation: vi.fn()
    })
}));

vi.mock('$lib/hooks/useAnnotationDeleteNavigation/useAnnotationDeleteNavigation', () => ({
    useAnnotationDeleteNavigation: () => ({
        gotoNextAnnotation: vi.fn()
    })
}));

vi.mock('$lib/services/addAnnotationDeleteToUndoStack', () => ({
    addAnnotationDeleteToUndoStack: vi.fn()
}));

vi.mock('svelte-sonner', () => ({
    toast: {
        error: toastErrorMock,
        success: vi.fn()
    }
}));

describe('SampleEraserRect', () => {
    const sample: { width: number; height: number; annotations: AnnotationView[] } = {
        width: 4,
        height: 4,
        annotations: [
            {
                parent_sample_id: 'parent-1',
                sample_id: 'ann-1',
                annotation_type: AnnotationType.INSTANCE_SEGMENTATION,
                annotation_label: { annotation_label_name: 'Car' },
                created_at: new Date('2026-03-20T00:00:00.000Z'),
                segmentation_details: {
                    x: 0,
                    y: 0,
                    width: 4,
                    height: 4,
                    segmentation_mask: [16]
                }
            }
        ]
    };

    const baseProps = {
        collectionId: 'collection-1',
        brushRadius: 3,
        drawerStrokeColor: 'rgb(0, 0, 255)',
        mousePosition: null,
        refetch: vi.fn()
    };

    beforeEach(() => {
        vi.clearAllMocks();
        mockAnnotationContext.annotationId = null;
        mockAnnotationContext.isDrawing = false;
        lockedAnnotationIds.clear();
    });

    it('auto-selects the annotation under the cursor when erasing starts', async () => {
        const { container } = render(SampleEraserRect, {
            props: {
                ...baseProps,
                sample
            }
        });

        const drawingRect = container.querySelector('rect');
        expect(drawingRect).not.toBeNull();

        await fireEvent.pointerDown(drawingRect as SVGRectElement, {
            pointerId: 1,
            clientX: 12,
            clientY: 12
        });

        expect(selectAnnotationMock).toHaveBeenCalledWith({
            annotationId: 'ann-1',
            annotations: sample.annotations,
            collectionId: 'collection-1'
        });
        expect(setIsDrawing).toHaveBeenCalledWith(true);
        expect(applyBrushToMaskMock).toHaveBeenCalled();
    });

    it('does not erase locked annotations', async () => {
        lockedAnnotationIds.add('ann-1');

        const { container } = render(SampleEraserRect, {
            props: {
                ...baseProps,
                sample
            }
        });

        const drawingRect = container.querySelector('rect');
        expect(drawingRect).not.toBeNull();

        await fireEvent.pointerDown(drawingRect as SVGRectElement, {
            pointerId: 1,
            clientX: 12,
            clientY: 12
        });

        expect(toastErrorMock).toHaveBeenCalledWith('This annotation is locked');
        expect(selectAnnotationMock).not.toHaveBeenCalled();
        expect(applyBrushToMaskMock).not.toHaveBeenCalled();
    });
});
