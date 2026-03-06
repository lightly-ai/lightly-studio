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
    width: number;
    height: number;
    masks: MaskInput[];
    boxes: BoundingBoxInput[];
    scaleX?: number;
    scaleY?: number;
};

type InitMessage = {
    type: 'init';
    canvas: OffscreenCanvas;
};

type WorkerMessage = RenderMessage | InitMessage;

let ctx: OffscreenCanvasRenderingContext2D | null = null;

const handleRender = ({ width, height, masks, boxes, scaleX = 1, scaleY = 1 }: RenderMessage) => {
    // Render masks into a pixel buffer and overlay boxes; stroke is scaled to CSS size.
    const pixelData = renderMasks(width, height, masks);
    const imageData = new ImageData(pixelData, width, height);
    const stroke = computeStroke(scaleX, scaleY);

    if (ctx) {
        ctx.canvas.width = width;
        ctx.canvas.height = height;
        ctx.clearRect(0, 0, width, height);
        ctx.putImageData(imageData, 0, 0);
        drawBoxesOnContext(ctx, boxes, width, height, stroke);
    } else {
        // Fallback: send pixel data and boxes back to main thread for painting.
        postMessage({ type: 'image', width, height, data: pixelData, boxes, stroke }, [
            pixelData.buffer
        ]);
    }
};

self.onmessage = (event: MessageEvent<WorkerMessage>) => {
    const message = event.data;

    if (message.type === 'init') {
        ctx = message.canvas.getContext('2d', { willReadFrequently: true });
        return;
    }

    if (message.type === 'render') {
        handleRender(message);
    }
};
