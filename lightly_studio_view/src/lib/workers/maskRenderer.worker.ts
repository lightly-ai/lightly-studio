/// <reference lib="webworker" />

import {
    type BoundingBoxInput,
    type MaskInput,
    computeStroke,
    drawBoxesOnContext,
    renderMasks
} from './maskRendererUtils';

type RenderMessage = {
    type: 'render';
    canvasId: string;
    width: number;
    height: number;
    masks: MaskInput[];
    boxes: BoundingBoxInput[];
    scaleX?: number;
    scaleY?: number;
};

type InitMessage = {
    type: 'init';
    canvasId: string;
    canvas: OffscreenCanvas;
};

type DisposeMessage = {
    type: 'dispose';
    canvasId: string;
};

type WorkerMessage = RenderMessage | InitMessage | DisposeMessage;

const contexts = new Map<string, OffscreenCanvasRenderingContext2D>();

const handleRender = ({
    canvasId,
    width,
    height,
    masks,
    boxes,
    scaleX = 1,
    scaleY = 1
}: RenderMessage) => {
    // Render masks into a pixel buffer and overlay boxes; stroke is scaled to CSS size.
    const pixelData = renderMasks(width, height, masks);
    const stroke = computeStroke(scaleX, scaleY);
    const ctx = contexts.get(canvasId);

    if (ctx) {
        const imageData = new ImageData(pixelData, width, height);
        ctx.canvas.width = width;
        ctx.canvas.height = height;
        ctx.clearRect(0, 0, width, height);
        ctx.putImageData(imageData, 0, 0);
        drawBoxesOnContext(ctx, boxes, width, height, stroke);
    } else {
        // Fallback: send pixel data and boxes back to main thread for painting.
        postMessage({ type: 'image', canvasId, width, height, data: pixelData, boxes, stroke }, [
            pixelData.buffer
        ]);
    }
};

self.onmessage = (event: MessageEvent<WorkerMessage>) => {
    const message = event.data;

    if (message.type === 'init') {
        const ctx = message.canvas.getContext('2d', { willReadFrequently: true });
        if (ctx) {
            contexts.set(message.canvasId, ctx);
        }
        return;
    }

    if (message.type === 'dispose') {
        contexts.delete(message.canvasId);
        return;
    }

    if (message.type === 'render') {
        handleRender(message);
    }
};
