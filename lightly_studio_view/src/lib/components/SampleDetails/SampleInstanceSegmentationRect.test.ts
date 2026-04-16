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
    decodeRLEToBinaryMaskMock,
    getImageCoordsFromMouseMock,
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

    const decodeRLEToBinaryMask = vi.fn();
    const getImageCoordsFromMouse = vi.fn(() => ({ x: 10, y: 12 }));
    const withAlpha = vi.fn(() => 'rgba(0, 0, 255, 0.25)');

    return {
        mockAnnotationContext: context,
        setAnnotationId: setAnnotationIdMock,
        setIsDrawing: setIsDrawingMock,
        committedSampleIds: sampleIds,
        useInstanceSegmentationBrushMock: brushHookMock,
        decodeRLEToBinaryMaskMock: decodeRLEToBinaryMask,
        getImageCoordsFromMouseMock: getImageCoordsFromMouse,
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
    decodeRLEToBinaryMask: decodeRLEToBinaryMaskMock,
    getImageCoordsFromMouse: getImageCoordsFromMouseMock,
    withAlpha: withAlphaMock
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

type Mock2dContext = {
    clearRect: ReturnType<typeof vi.fn>;
    createImageData: ReturnType<typeof vi.fn>;
    putImageData: ReturnType<typeof vi.fn>;
    drawImage: ReturnType<typeof vi.fn>;
    fillRect: ReturnType<typeof vi.fn>;
    getImageData: ReturnType<typeof vi.fn>;
    beginPath: ReturnType<typeof vi.fn>;
    arc: ReturnType<typeof vi.fn>;
    fill: ReturnType<typeof vi.fn>;
    moveTo: ReturnType<typeof vi.fn>;
    lineTo: ReturnType<typeof vi.fn>;
    stroke: ReturnType<typeof vi.fn>;
    globalCompositeOperation: string;
    fillStyle: string;
    strokeStyle: string;
    lineWidth: number;
    lineCap: CanvasLineCap;
    lineJoin: CanvasLineJoin;
};

let nextFrameId = 1;
let scheduledFrames: ScheduledFrame[] = [];
let mockCanvasContext: Mock2dContext;

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

const getPreviewLayer = (container: HTMLElement): SVGForeignObjectElement => {
    const previewLayer = container.querySelector('foreignObject');
    expect(previewLayer).not.toBeNull();
    return previewLayer as SVGForeignObjectElement;
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

        mockCanvasContext = {
            clearRect: vi.fn(),
            createImageData: vi.fn((width: number, height: number) => ({
                data: new Uint8ClampedArray(width * height * 4),
                width,
                height
            })),
            putImageData: vi.fn(),
            drawImage: vi.fn(),
            fillRect: vi.fn(),
            getImageData: vi.fn((x: number, y: number, width: number, height: number) => ({
                data: new Uint8ClampedArray(width * height * 4),
                width,
                height
            })),
            beginPath: vi.fn(),
            arc: vi.fn(),
            fill: vi.fn(),
            moveTo: vi.fn(),
            lineTo: vi.fn(),
            stroke: vi.fn(),
            globalCompositeOperation: 'source-over',
            fillStyle: 'black',
            strokeStyle: 'black',
            lineWidth: 1,
            lineCap: 'round',
            lineJoin: 'round'
        };

        vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(
            (contextId: string) => {
                if (contextId !== '2d') return null;
                return mockCanvasContext as unknown as CanvasRenderingContext2D;
            }
        );

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
        vi.restoreAllMocks();
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
        expect(mockCanvasContext.drawImage).not.toHaveBeenCalled();
        expect(getPreviewLayer(container).classList.contains('previewHidden')).toBe(true);

        await runNextFrame();

        expect(mockCanvasContext.drawImage).toHaveBeenCalledTimes(1);
        expect(getPreviewLayer(container).classList.contains('previewHidden')).toBe(false);
    });

    it('replaces a queued preview animation frame with the latest update', async () => {
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

    it('notifies pending state while finishBrush is in flight', async () => {
        let resolveFinishBrush: (() => void) | undefined;
        const finishBrush = vi.fn(
            () =>
                new Promise<void>((resolve) => {
                    resolveFinishBrush = resolve;
                })
        );
        useInstanceSegmentationBrushMock.mockReturnValueOnce({ finishBrush });
        const onFinishBrushPendingChange = vi.fn();

        const { container } = render(SampleInstanceSegmentationRect, {
            props: {
                ...baseProps,
                sampleId: 'sample-1',
                sample: { width: 100, height: 100, annotations: [] },
                onFinishBrushPendingChange
            }
        });

        const drawingRect = getDrawingRect(container);
        await fireEvent.pointerDown(drawingRect, {
            pointerId: 1,
            clientX: 20,
            clientY: 20
        });
        await fireEvent.pointerUp(drawingRect, { pointerId: 1 });

        expect(onFinishBrushPendingChange).toHaveBeenCalledWith(true);

        resolveFinishBrush?.();
        await tick();

        expect(onFinishBrushPendingChange).toHaveBeenLastCalledWith(false);
    });
});
