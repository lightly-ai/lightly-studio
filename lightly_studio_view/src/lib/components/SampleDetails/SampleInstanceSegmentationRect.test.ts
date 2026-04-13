import { fireEvent, render } from '@testing-library/svelte';
import { tick } from 'svelte';
import { writable } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SampleInstanceSegmentationRect from './SampleInstanceSegmentationRect/SampleInstanceSegmentationRect.svelte';

const {
    mockAnnotationContext,
    setAnnotationId,
    setIsDrawing,
    committedSampleIds,
    useInstanceSegmentationBrushMock,
    applyBrushToMaskMock,
    decodeRLEToBinaryMaskMock,
    getImageCoordsFromMouseMock,
    interpolateLineBetweenPointsMock,
    maskToDataUrlMock,
    withAlphaMock
} = vi.hoisted(() => {
    const context = {
        annotationId: null as string | null,
        isDrawing: false,
        isOnAnnotationDetailsView: false
    };

    const setAnnotationIdMock = vi.fn((id: string | null) => {
        context.annotationId = id;
    });
    const setIsDrawingMock = vi.fn((value: boolean) => {
        context.isDrawing = value;
    });

    const sampleIds: string[] = [];
    const brushHookMock = vi.fn((params: { sampleId: string }) => ({
        finishBrush: vi.fn(() => {
            sampleIds.push(params.sampleId);
        })
    }));

    const applyBrushToMask = vi.fn();
    const decodeRLEToBinaryMask = vi.fn();
    const getImageCoordsFromMouse = vi.fn(() => ({ x: 10, y: 12 }));
    const interpolateLineBetweenPoints = vi.fn(() => []);
    const maskToDataUrl = vi.fn(() => 'data:image/png;base64,preview');
    const withAlpha = vi.fn(() => 'rgba(0, 0, 255, 0.25)');

    return {
        mockAnnotationContext: context,
        setAnnotationId: setAnnotationIdMock,
        setIsDrawing: setIsDrawingMock,
        committedSampleIds: sampleIds,
        useInstanceSegmentationBrushMock: brushHookMock,
        applyBrushToMaskMock: applyBrushToMask,
        decodeRLEToBinaryMaskMock: decodeRLEToBinaryMask,
        getImageCoordsFromMouseMock: getImageCoordsFromMouse,
        interpolateLineBetweenPointsMock: interpolateLineBetweenPoints,
        maskToDataUrlMock: maskToDataUrl,
        withAlphaMock: withAlpha
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
    applyBrushToMask: applyBrushToMaskMock,
    decodeRLEToBinaryMask: decodeRLEToBinaryMaskMock,
    getImageCoordsFromMouse: getImageCoordsFromMouseMock,
    interpolateLineBetweenPoints: interpolateLineBetweenPointsMock,
    maskToDataUrl: maskToDataUrlMock,
    withAlpha: withAlphaMock
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

const baseProps = {
    collectionId: 'collection-1',
    brushRadius: 5,
    drawerStrokeColor: 'rgb(0, 0, 255)',
    mousePosition: null,
    refetch: vi.fn()
};

type ScheduledFrame = {
    id: number;
    callback: FrameRequestCallback;
};

let nextFrameId = 1;
let scheduledFrames: ScheduledFrame[] = [];

const runNextFrame = async () => {
    const next = scheduledFrames.shift();
    expect(next).toBeTruthy();
    next!.callback(16);
    await tick();
};

const getDrawingRect = (container: HTMLElement): SVGRectElement => {
    const drawingRect = container.querySelector('rect');
    expect(drawingRect).not.toBeNull();
    return drawingRect as SVGRectElement;
};

describe('SampleInstanceSegmentationRect', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockAnnotationContext.annotationId = null;
        mockAnnotationContext.isDrawing = false;
        mockAnnotationContext.isOnAnnotationDetailsView = false;
        committedSampleIds.length = 0;
        nextFrameId = 1;
        scheduledFrames = [];
        baseProps.refetch.mockReset();

        vi.stubGlobal(
            'requestAnimationFrame',
            vi.fn((callback: FrameRequestCallback) => {
                const id = nextFrameId++;
                scheduledFrames.push({ id, callback });
                return id;
            })
        );

        vi.stubGlobal(
            'cancelAnimationFrame',
            vi.fn((id: number) => {
                scheduledFrames = scheduledFrames.filter(
                    (scheduledFrame) => scheduledFrame.id !== id
                );
            })
        );
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it('uses the latest sample id for brush commit after rerender', async () => {
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

        const drawingRect = getDrawingRect(container);

        await fireEvent.pointerDown(drawingRect, {
            pointerId: 1,
            clientX: 20,
            clientY: 20
        });
        await fireEvent.pointerUp(drawingRect, { pointerId: 1 });

        expect(committedSampleIds).toEqual(['sample-2']);
    });

    it('renders preview only after the animation frame callback runs', async () => {
        const { container } = render(SampleInstanceSegmentationRect, {
            props: {
                ...baseProps,
                sampleId: 'sample-1',
                sample: { width: 100, height: 100, annotations: [] }
            }
        });

        const drawingRect = getDrawingRect(container);
        await fireEvent.pointerDown(drawingRect, {
            pointerId: 1,
            clientX: 20,
            clientY: 20
        });

        expect(requestAnimationFrame).toHaveBeenCalledTimes(1);
        expect(maskToDataUrlMock).not.toHaveBeenCalled();
        expect(container.querySelector('image')).toBeNull();

        await runNextFrame();

        expect(maskToDataUrlMock).toHaveBeenCalledTimes(1);
        expect(container.querySelector('image')).not.toBeNull();
    });

    it('cancels the previous scheduled frame before scheduling a new preview update', async () => {
        const { container } = render(SampleInstanceSegmentationRect, {
            props: {
                ...baseProps,
                sampleId: 'sample-1',
                sample: { width: 100, height: 100, annotations: [] }
            }
        });

        const drawingRect = getDrawingRect(container);
        await fireEvent.pointerDown(drawingRect, {
            pointerId: 1,
            clientX: 20,
            clientY: 20
        });
        await fireEvent.pointerMove(drawingRect, {
            pointerId: 1,
            clientX: 21,
            clientY: 21
        });

        expect(requestAnimationFrame).toHaveBeenCalledTimes(2);
        expect(cancelAnimationFrame).toHaveBeenCalledTimes(1);
        expect(cancelAnimationFrame).toHaveBeenCalledWith(1);
        expect(scheduledFrames).toHaveLength(1);
        expect(scheduledFrames[0]?.id).toBe(2);
    });

    it('cancels scheduled preview updates when the component unmounts', async () => {
        const { container, unmount } = render(SampleInstanceSegmentationRect, {
            props: {
                ...baseProps,
                sampleId: 'sample-1',
                sample: { width: 100, height: 100, annotations: [] }
            }
        });

        const drawingRect = getDrawingRect(container);
        await fireEvent.pointerDown(drawingRect, {
            pointerId: 1,
            clientX: 20,
            clientY: 20
        });

        unmount();

        expect(cancelAnimationFrame).toHaveBeenCalledTimes(1);
        expect(cancelAnimationFrame).toHaveBeenCalledWith(1);
        expect(scheduledFrames).toHaveLength(0);
    });

    it('cancels a scheduled preview update when annotation state is reset by rerender', async () => {
        mockAnnotationContext.annotationId = 'annotation-1';

        const { container, rerender } = render(SampleInstanceSegmentationRect, {
            props: {
                ...baseProps,
                sampleId: 'sample-1',
                sample: {
                    width: 100,
                    height: 100,
                    annotations: [
                        {
                            parent_sample_id: 'parent-sample-1',
                            sample_id: 'annotation-1',
                            annotation_type: 'instance_segmentation',
                            annotation_label: { annotation_label_name: 'label-1' },
                            created_at: new Date('1970-01-01T00:00:00.000Z'),
                            segmentation_details: {
                                x: 0,
                                y: 0,
                                width: 100,
                                height: 100,
                                segmentation_mask: null
                            }
                        }
                    ]
                }
            }
        });

        const drawingRect = getDrawingRect(container);
        await fireEvent.pointerDown(drawingRect, {
            pointerId: 1,
            clientX: 20,
            clientY: 20
        });

        await rerender({
            ...baseProps,
            sampleId: 'sample-1',
            sample: { width: 100, height: 100, annotations: [] }
        });

        expect(cancelAnimationFrame).toHaveBeenCalledTimes(1);
        expect(cancelAnimationFrame).toHaveBeenCalledWith(1);
        expect(scheduledFrames).toHaveLength(0);
    });
});
