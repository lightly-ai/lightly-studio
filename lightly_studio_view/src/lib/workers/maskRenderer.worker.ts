/// <reference lib="webworker" />

import {
    type BoundingBoxInput,
    type MaskInput,
    drawBoxesOnContext,
    renderMasks,
    transformBoxes,
    type RenderGeometry,
    type SourceCrop
} from './maskRendererUtils';

interface RenderMessage {
    type: 'render';
    canvasId: string;
    sourceWidth: number;
    sourceHeight: number;
    outputWidth: number;
    outputHeight: number;
    objectFit: 'contain' | 'cover';
    sourceCrop?: SourceCrop;
    masks: MaskInput[];
    boxes: BoundingBoxInput[];
}

interface InitMessage {
    type: 'init';
    canvasId: string;
    canvas: OffscreenCanvas;
}

interface DisposeMessage {
    type: 'dispose';
    canvasId: string;
}

type WorkerMessage = RenderMessage | InitMessage | DisposeMessage;

// One worker can serve multiple canvases; each canvas keeps its own 2D context keyed by id.
const contexts = new Map<string, OffscreenCanvasRenderingContext2D>();

const handleRender = ({
    canvasId,
    sourceWidth,
    sourceHeight,
    outputWidth,
    outputHeight,
    objectFit,
    sourceCrop,
    masks,
    boxes
}: RenderMessage) => {
    const geometry: RenderGeometry = {
        sourceWidth,
        sourceHeight,
        outputWidth,
        outputHeight,
        objectFit,
        sourceCrop
    };
    const pixelData = renderMasks(geometry, masks);
    const transformedBoxes = transformBoxes(geometry, boxes);
    const ctx = contexts.get(canvasId);

    if (ctx) {
        // Offscreen path: paint fully inside worker.
        const imageData = new ImageData(pixelData, outputWidth, outputHeight);
        ctx.canvas.width = outputWidth;
        ctx.canvas.height = outputHeight;
        ctx.clearRect(0, 0, outputWidth, outputHeight);
        ctx.putImageData(imageData, 0, 0);
        drawBoxesOnContext(ctx, transformedBoxes);
    } else {
        // Fallback path when no OffscreenCanvas context was registered for this canvas id.
        // renderMasks deliberately returns an ArrayBuffer-backed view because transferable
        // payloads cannot use SharedArrayBuffer as their ownership-transfer list entry.
        postMessage(
            {
                type: 'image',
                canvasId,
                width: outputWidth,
                height: outputHeight,
                data: pixelData,
                boxes: transformedBoxes
            },
            [pixelData.buffer]
        );
    }
};

self.onmessage = (event: MessageEvent<WorkerMessage>) => {
    const message = event.data;

    if (message.type === 'init') {
        // Register or replace the drawing context for this canvas id.
        const ctx = message.canvas.getContext('2d', { willReadFrequently: true });
        if (ctx) {
            contexts.set(message.canvasId, ctx);
        }
        return;
    }

    if (message.type === 'dispose') {
        // Canvas unmounted on main thread; release its context from this worker.
        contexts.delete(message.canvasId);
        return;
    }

    if (message.type === 'render') {
        handleRender(message);
    }
};
