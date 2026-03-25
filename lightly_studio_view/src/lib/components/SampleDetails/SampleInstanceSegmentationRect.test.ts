import { fireEvent, render } from '@testing-library/svelte';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { writable } from 'svelte/store';
import SampleInstanceSegmentationRect from './SampleInstanceSegmentationRect/SampleInstanceSegmentationRect.svelte';

const {
    mockAnnotationContext,
    mockToolbarContext,
    setAnnotationId,
    setIsDrawing,
    committedSampleIds,
    brushHookCalls,
    useInstanceSegmentationBrushMock
} = vi.hoisted(() => {
    const context = {
        annotationId: null as string | null,
        isDrawing: false,
        isOnAnnotationDetailsView: false
    };
    const toolbarContext = {
        brush: {
            oneClassPerPixel: false
        }
    };

    const setAnnotationIdMock = vi.fn((id: string | null) => {
        context.annotationId = id;
    });
    const setIsDrawingMock = vi.fn((value: boolean) => {
        context.isDrawing = value;
    });

    const sampleIds: string[] = [];
    const hookCalls: {
        sampleId: string;
        segmentationMode?: string;
        annotationType?: string;
        oneClassPerPixel?: boolean;
    }[] = [];
    const brushHookMock = vi.fn(
        (params: {
            sampleId: string;
            segmentationMode?: string;
            annotationType?: string;
            oneClassPerPixel?: boolean;
        }) => {
            hookCalls.push(params);
            return {
                finishBrush: vi.fn(() => {
                    sampleIds.push(params.sampleId);
                })
            };
        }
    );

    return {
        mockAnnotationContext: context,
        mockToolbarContext: toolbarContext,
        setAnnotationId: setAnnotationIdMock,
        setIsDrawing: setIsDrawingMock,
        committedSampleIds: sampleIds,
        brushHookCalls: hookCalls,
        useInstanceSegmentationBrushMock: brushHookMock
    };
});

vi.mock('$app/state', () => ({
    page: {
        params: {
            dataset_id: 'dataset-1'
        }
    }
}));

vi.mock('$lib/components/SampleAnnotation/utils', () => ({
    applyBrushToMask: vi.fn(),
    decodeRLEToBinaryMask: vi.fn(),
    getImageCoordsFromMouse: vi.fn(() => ({ x: 10, y: 12 })),
    interpolateLineBetweenPoints: vi.fn(() => []),
    maskToDataUrl: vi.fn(() => 'data:image/png;base64,preview'),
    withAlpha: vi.fn(() => 'rgba(0, 0, 255, 0.25)')
}));

vi.mock(
    '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/calculateBinaryMaskFromRLE/parseColor',
    () => ({
        default: vi.fn(() => [0, 0, 255, 255])
    })
);

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({
        context: mockAnnotationContext,
        setIsDrawing,
        setAnnotationId
    })
}));

vi.mock('$lib/contexts/SampleDetailsToolbar.svelte', () => ({
    useSampleDetailsToolbarContext: () => ({
        context: mockToolbarContext
    })
}));

vi.mock('$lib/hooks/useAnnotation/useAnnotation', () => ({
    useAnnotation: () => ({
        updateAnnotation: vi.fn()
    })
}));

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () =>
        writable({
            data: []
        })
}));

vi.mock('$lib/hooks/useCollection/useCollection', () => ({
    useCollectionWithChildren: () => ({
        refetch: vi.fn()
    })
}));

vi.mock('$lib/hooks/useInstanceSegmentationBrush', () => ({
    useInstanceSegmentationBrush: useInstanceSegmentationBrushMock
}));

describe('SampleInstanceSegmentationRect', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockAnnotationContext.annotationId = null;
        mockAnnotationContext.isDrawing = false;
        mockToolbarContext.brush.oneClassPerPixel = false;
        committedSampleIds.length = 0;
        brushHookCalls.length = 0;
    });

    it('uses the latest sample id for brush commit after rerender', async () => {
        const baseProps = {
            collectionId: 'collection-1',
            brushRadius: 5,
            drawerStrokeColor: 'rgb(0, 0, 255)',
            mousePosition: null,
            refetch: vi.fn()
        };

        const { container, rerender } = render(SampleInstanceSegmentationRect, {
            props: {
                ...baseProps,
                sampleId: 'sample-1',
                sample: { width: 100, height: 100, annotations: [] }
            }
        });

        await rerender({
            ...baseProps,
            sampleId: 'sample-2',
            sample: { width: 100, height: 100, annotations: [] }
        });

        const drawingRect = container.querySelector('rect');
        expect(drawingRect).not.toBeNull();

        await fireEvent.pointerDown(drawingRect as SVGRectElement, {
            pointerId: 1,
            clientX: 20,
            clientY: 20
        });
        await fireEvent.pointerUp(drawingRect as SVGRectElement, { pointerId: 1 });

        expect(committedSampleIds).toEqual(['sample-2']);
    });

    it('switches to one-class overlap mode when one class per pixel is enabled', async () => {
        mockToolbarContext.brush.oneClassPerPixel = true;

        const { container } = render(SampleInstanceSegmentationRect, {
            props: {
                collectionId: 'collection-1',
                sampleId: 'sample-1',
                brushRadius: 5,
                drawerStrokeColor: 'rgb(0, 0, 255)',
                mousePosition: null,
                refetch: vi.fn(),
                sample: { width: 100, height: 100, annotations: [] }
            }
        });

        const drawingRect = container.querySelector('rect');
        expect(drawingRect).not.toBeNull();

        await fireEvent.pointerDown(drawingRect as SVGRectElement, {
            pointerId: 1,
            clientX: 20,
            clientY: 20
        });
        await fireEvent.pointerUp(drawingRect as SVGRectElement, { pointerId: 1 });

        expect(brushHookCalls.at(-1)).toMatchObject({
            segmentationMode: 'instance',
            annotationType: 'instance_segmentation',
            oneClassPerPixel: true
        });
    });
});
