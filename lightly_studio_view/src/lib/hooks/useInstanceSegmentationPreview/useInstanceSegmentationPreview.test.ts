import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useInstanceSegmentationPreview } from './useInstanceSegmentationPreview';

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

describe('useInstanceSegmentationPreview', () => {
    let previewCanvas: HTMLCanvasElement;
    let previewContext: Mock2dContext;
    let sourceContext: Mock2dContext;
    let nextFrameId: number;
    let scheduledFrames: ScheduledFrame[];

    const runNextFrame = () => {
        const next = scheduledFrames.shift();
        expect(next).toBeTruthy();
        next!.callback(16);
    };

    beforeEach(() => {
        vi.clearAllMocks();

        previewCanvas = document.createElement('canvas');
        previewCanvas.width = 2;
        previewCanvas.height = 2;

        nextFrameId = 1;
        scheduledFrames = [];

        previewContext = {
            clearRect: vi.fn(),
            createImageData: vi.fn((width: number, height: number) => ({
                data: new Uint8ClampedArray(width * height * 4),
                width,
                height
            })),
            putImageData: vi.fn(),
            drawImage: vi.fn(),
            fillRect: vi.fn(),
            getImageData: vi.fn(() => ({
                data: new Uint8ClampedArray(2 * 2 * 4),
                width: 2,
                height: 2
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

        sourceContext = {
            clearRect: vi.fn(),
            createImageData: vi.fn((width: number, height: number) => ({
                data: new Uint8ClampedArray(width * height * 4),
                width,
                height
            })),
            putImageData: vi.fn(),
            drawImage: vi.fn(),
            fillRect: vi.fn(),
            getImageData: vi.fn(() => ({
                data: new Uint8ClampedArray(2 * 2 * 4),
                width: 2,
                height: 2
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

        vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(function (
            this: HTMLCanvasElement,
            contextId: string
        ) {
            if (contextId !== '2d') return null;
            if (this === previewCanvas) {
                return previewContext as unknown as CanvasRenderingContext2D;
            }

            return sourceContext as unknown as CanvasRenderingContext2D;
        });

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
                scheduledFrames = scheduledFrames.filter((frame) => frame.id !== id);
            })
        );
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('draws a binary mask into the source canvas alpha channel', () => {
        const hook = useInstanceSegmentationPreview();

        hook.drawMaskToCanvas(new Uint8Array([0, 1, 0, 1]), 2, 2);

        expect(sourceContext.createImageData).toHaveBeenCalledWith(2, 2);
        expect(sourceContext.putImageData).toHaveBeenCalledTimes(1);

        const imageData = sourceContext.putImageData.mock.calls[0][0] as ImageData;
        expect(imageData.data[3]).toBe(0);
        expect(imageData.data[7]).toBe(255);
        expect(imageData.data[11]).toBe(0);
        expect(imageData.data[15]).toBe(255);
    });

    it('supports destination-out compositing for eraser strokes', () => {
        const hook = useInstanceSegmentationPreview();

        hook.drawBrushDot({
            point: { x: 1, y: 1 },
            brushRadius: 4,
            width: 2,
            height: 2,
            compositeOperation: 'destination-out'
        });

        hook.drawBrushLine({
            from: { x: 0, y: 0 },
            to: { x: 1, y: 1 },
            brushRadius: 4,
            width: 2,
            height: 2,
            compositeOperation: 'destination-out'
        });

        expect(sourceContext.globalCompositeOperation).toBe('destination-out');
        expect(sourceContext.arc).toHaveBeenCalledTimes(1);
        expect(sourceContext.stroke).toHaveBeenCalledTimes(1);
    });

    it('keeps only the latest scheduled preview composition and updates visibility', () => {
        const onPreviewVisibilityChange = vi.fn();
        const hook = useInstanceSegmentationPreview({ onPreviewVisibilityChange });
        hook.setPreviewCanvas(previewCanvas);
        hook.drawMaskToCanvas(new Uint8Array([1, 0, 0, 0]), 2, 2);

        hook.schedulePreviewCompose({
            width: 2,
            height: 2,
            color: { r: 0, g: 0, b: 255, a: 255 },
            isDrawing: true
        });
        hook.schedulePreviewCompose({
            width: 2,
            height: 2,
            color: { r: 0, g: 0, b: 255, a: 255 },
            isDrawing: true
        });

        expect(requestAnimationFrame).toHaveBeenCalledTimes(2);
        expect(cancelAnimationFrame).toHaveBeenCalledTimes(1);
        expect(cancelAnimationFrame).toHaveBeenCalledWith(1);
        expect(previewContext.drawImage).not.toHaveBeenCalled();

        runNextFrame();

        expect(previewContext.drawImage).toHaveBeenCalledTimes(1);
        expect(previewContext.fillRect).toHaveBeenCalledTimes(1);
        expect(onPreviewVisibilityChange).toHaveBeenCalledWith(true);
    });

    it('uses the latest scheduled draw state when replacing a queued frame', () => {
        const onPreviewVisibilityChange = vi.fn();
        const hook = useInstanceSegmentationPreview({ onPreviewVisibilityChange });
        hook.setPreviewCanvas(previewCanvas);
        hook.drawMaskToCanvas(new Uint8Array([1, 0, 0, 0]), 2, 2);

        hook.schedulePreviewCompose({
            width: 2,
            height: 2,
            color: { r: 0, g: 0, b: 255, a: 255 },
            isDrawing: true
        });
        hook.schedulePreviewCompose({
            width: 2,
            height: 2,
            color: { r: 0, g: 0, b: 255, a: 255 },
            isDrawing: false
        });

        runNextFrame();

        expect(previewContext.drawImage).not.toHaveBeenCalled();
        expect(onPreviewVisibilityChange).not.toHaveBeenCalledWith(true);
    });

    it('does not compose preview when drawing is disabled', () => {
        const onPreviewVisibilityChange = vi.fn();
        const hook = useInstanceSegmentationPreview({ onPreviewVisibilityChange });
        hook.setPreviewCanvas(previewCanvas);
        hook.drawMaskToCanvas(new Uint8Array([1, 0, 0, 0]), 2, 2);

        hook.schedulePreviewCompose({
            width: 2,
            height: 2,
            color: { r: 0, g: 0, b: 255, a: 255 },
            isDrawing: false
        });

        runNextFrame();

        expect(previewContext.drawImage).not.toHaveBeenCalled();
        expect(onPreviewVisibilityChange).not.toHaveBeenCalledWith(true);
    });

    it('extracts binary mask from source canvas alpha channel', () => {
        sourceContext.getImageData.mockReturnValue({
            data: new Uint8ClampedArray([0, 0, 0, 0, 0, 0, 0, 255, 0, 0, 0, 0, 0, 0, 0, 255]),
            width: 2,
            height: 2
        });

        const hook = useInstanceSegmentationPreview();
        hook.drawMaskToCanvas(null, 2, 2);

        const mask = hook.toBinaryMaskFromCanvas(2, 2);

        expect(mask).not.toBeNull();
        expect(Array.from(mask ?? [])).toEqual([0, 1, 0, 1]);
    });

    it('cancels scheduled preview compose', () => {
        const hook = useInstanceSegmentationPreview();
        hook.setPreviewCanvas(previewCanvas);
        hook.drawMaskToCanvas(new Uint8Array([1, 0, 0, 0]), 2, 2);

        hook.schedulePreviewCompose({
            width: 2,
            height: 2,
            color: { r: 0, g: 0, b: 255, a: 255 },
            isDrawing: true
        });

        hook.cancelScheduledPreviewCompose();

        expect(cancelAnimationFrame).toHaveBeenCalledTimes(1);
        expect(cancelAnimationFrame).toHaveBeenCalledWith(1);
        expect(scheduledFrames).toHaveLength(0);
    });

    it('cancels scheduled preview compose when clearing preview', () => {
        const hook = useInstanceSegmentationPreview();
        hook.setPreviewCanvas(previewCanvas);
        hook.drawMaskToCanvas(new Uint8Array([1, 0, 0, 0]), 2, 2);

        hook.schedulePreviewCompose({
            width: 2,
            height: 2,
            color: { r: 0, g: 0, b: 255, a: 255 },
            isDrawing: true
        });
        hook.clearPreview();

        expect(cancelAnimationFrame).toHaveBeenCalledTimes(1);
        expect(cancelAnimationFrame).toHaveBeenCalledWith(1);
        expect(scheduledFrames).toHaveLength(0);
        expect(previewContext.clearRect).toHaveBeenCalledWith(0, 0, 2, 2);
    });
});
