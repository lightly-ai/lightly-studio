import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { tick } from 'svelte';
import AnnotationCanvas from './AnnotationCanvas.svelte';

vi.mock('$lib/utils', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/utils')>()),
    getColorByLabel: vi.fn(() => ({
        color: 'rgba(10, 20, 30, 0.5)',
        contrastColor: 'rgba(245, 235, 225, 1)'
    }))
}));

type Mock2dContext = {
    fillStyle: string;
    strokeStyle: string;
    lineWidth: number;
    clearRect: ReturnType<typeof vi.fn>;
    fillRect: ReturnType<typeof vi.fn>;
    getImageData: ReturnType<typeof vi.fn>;
    putImageData: ReturnType<typeof vi.fn>;
    save: ReturnType<typeof vi.fn>;
    restore: ReturnType<typeof vi.fn>;
    strokeRect: ReturnType<typeof vi.fn>;
};

class MockWorker {
    static instances: MockWorker[] = [];
    onmessage: ((event: MessageEvent) => void) | null = null;
    postMessage = vi.fn();
    private messageListeners = new Set<(event: MessageEvent) => void>();
    addEventListener = vi.fn((type: string, listener: EventListenerOrEventListenerObject) => {
        if (type !== 'message') {
            return;
        }

        if (typeof listener === 'function') {
            this.messageListeners.add(listener as (event: MessageEvent) => void);
        }
    });
    removeEventListener = vi.fn((type: string, listener: EventListenerOrEventListenerObject) => {
        if (type !== 'message') {
            return;
        }

        if (typeof listener === 'function') {
            this.messageListeners.delete(listener as (event: MessageEvent) => void);
        }
    });
    terminate = vi.fn();

    constructor() {
        MockWorker.instances.push(this);
    }

    dispatchMessage(data: unknown) {
        const event = { data } as MessageEvent;
        for (const listener of this.messageListeners) {
            listener(event);
        }
    }
}

class MockImageData {
    constructor(
        public data: Uint8ClampedArray,
        public width: number,
        public height: number
    ) {}
}

describe('AnnotationCanvas', () => {
    let canvasContexts: WeakMap<HTMLCanvasElement, Mock2dContext>;
    const createMockContext = (): Mock2dContext => ({
        fillStyle: 'rgba(0, 0, 0, 0)',
        strokeStyle: 'rgba(0, 0, 0, 0)',
        lineWidth: 1,
        clearRect: vi.fn(),
        fillRect: vi.fn(),
        getImageData: vi.fn(() => ({ data: new Uint8ClampedArray([10, 20, 30, 128]) })),
        putImageData: vi.fn(),
        save: vi.fn(),
        restore: vi.fn(),
        strokeRect: vi.fn()
    });

    beforeEach(() => {
        MockWorker.instances = [];
        canvasContexts = new WeakMap<HTMLCanvasElement, Mock2dContext>();

        vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(function (
            this: HTMLCanvasElement,
            contextId: string
        ) {
            if (contextId !== '2d') {
                return null;
            }

            if (!canvasContexts.has(this)) {
                canvasContexts.set(this, createMockContext());
            }

            return canvasContexts.get(this) as unknown as CanvasRenderingContext2D;
        });

        vi.stubGlobal('Worker', MockWorker as unknown as typeof Worker);
        vi.stubGlobal('ImageData', MockImageData as unknown as typeof ImageData);
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
        Reflect.deleteProperty(HTMLCanvasElement.prototype, 'transferControlToOffscreen');
    });

    afterEach(async () => {
        const { shutdownMaskRendererPool } = await import('$lib/workers/maskRendererPool');
        shutdownMaskRendererPool();
    });

    it('draws object-detection boxes on fallback canvas when there are no masks', async () => {
        const { container } = render(AnnotationCanvas, {
            props: {
                sampleId: 'sample-object-detection',
                sourceWidth: 8192,
                sourceHeight: 8192,
                outputWidth: 200,
                outputHeight: 200,
                annotations: [
                    {
                        annotation_type: 'object_detection',
                        annotation_label_name: 'car',
                        object_detection_details: {
                            x: 1024,
                            y: 2048,
                            width: 3072,
                            height: 4096
                        }
                    }
                ]
            }
        });

        await tick();
        const canvas = container.querySelector('canvas');
        expect(canvas).not.toBeNull();
        const context = canvasContexts.get(canvas as HTMLCanvasElement);
        expect(context).toBeDefined();

        expect(MockWorker.instances).toHaveLength(0);
        expect(canvas).toHaveAttribute('width', '200');
        expect(canvas).toHaveAttribute('height', '200');
        expect(context?.clearRect).toHaveBeenCalledWith(0, 0, 200, 200);
        expect(context?.strokeRect).toHaveBeenCalledWith(25, 50, 75, 100);
    });

    it('keeps source-sized canvas defaults for consumers without output dimensions', async () => {
        const { container } = render(AnnotationCanvas, {
            props: {
                sampleId: 'source-sized-default',
                sourceWidth: 100,
                sourceHeight: 80,
                annotations: [
                    {
                        annotation_type: 'object_detection',
                        annotation_label_name: 'car',
                        object_detection_details: { x: 10, y: 20, width: 30, height: 40 }
                    }
                ]
            }
        });

        await tick();

        const canvas = container.querySelector('canvas');
        expect(canvas).toHaveAttribute('width', '100');
        expect(canvas).toHaveAttribute('height', '80');
        expect(canvasContexts.get(canvas as HTMLCanvasElement)?.strokeRect).toHaveBeenCalledWith(
            10,
            20,
            30,
            40
        );
    });

    it('posts a worker render message when masks are present', async () => {
        render(AnnotationCanvas, {
            props: {
                sampleId: 'sample-masks',
                sourceWidth: 16,
                sourceHeight: 8,
                outputWidth: 8,
                outputHeight: 4,
                annotations: [
                    {
                        annotation_type: 'segmentation_mask',
                        annotation_label_name: 'road',
                        segmentation_mask: [0, 3, 2]
                    }
                ]
            }
        });

        await tick();

        expect(MockWorker.instances.length).toBeGreaterThan(0);
        const workersWithRender = MockWorker.instances.filter((instance) =>
            instance.postMessage.mock.calls.some(([message]) => message?.type === 'render')
        );
        expect(workersWithRender).toHaveLength(1);
        const worker = workersWithRender[0];
        const [canvas] = Array.from(document.querySelectorAll('canvas'));
        const context = canvas ? canvasContexts.get(canvas as HTMLCanvasElement) : undefined;
        expect(context?.clearRect).toHaveBeenCalledWith(0, 0, 8, 4);
        expect(worker.postMessage).toHaveBeenCalledTimes(1);
        expect(worker.postMessage).toHaveBeenCalledWith(
            expect.objectContaining({
                type: 'render',
                sourceWidth: 16,
                sourceHeight: 8,
                outputWidth: 8,
                outputHeight: 4,
                objectFit: 'contain',
                boxes: [],
                masks: [expect.objectContaining({ rle: [0, 3, 2] })]
            })
        );
    });

    it('clears and exits early when there are no drawable annotations', async () => {
        const { container } = render(AnnotationCanvas, {
            props: {
                sampleId: 'sample-empty',
                sourceWidth: 64,
                sourceHeight: 32,
                outputWidth: 32,
                outputHeight: 16,
                annotations: []
            }
        });

        await tick();
        const canvas = container.querySelector('canvas');
        expect(canvas).not.toBeNull();
        const context = canvasContexts.get(canvas as HTMLCanvasElement);
        expect(context).toBeDefined();

        expect(MockWorker.instances).toHaveLength(0);
        expect(context?.clearRect).toHaveBeenCalledWith(0, 0, 32, 16);
        expect(context?.strokeRect).not.toHaveBeenCalled();
    });

    it('re-renders the same bounded canvas when the tile size changes', async () => {
        const { container, rerender } = render(AnnotationCanvas, {
            props: {
                sampleId: 'resized-sample',
                sourceWidth: 1000,
                sourceHeight: 1000,
                outputWidth: 200,
                outputHeight: 200,
                annotations: [
                    {
                        annotation_type: 'object_detection',
                        annotation_label_name: 'car',
                        object_detection_details: { x: 100, y: 100, width: 200, height: 200 }
                    }
                ]
            }
        });
        await tick();

        await rerender({
            sampleId: 'resized-sample',
            sourceWidth: 1000,
            sourceHeight: 1000,
            outputWidth: 300,
            outputHeight: 300,
            annotations: [
                {
                    annotation_type: 'object_detection',
                    annotation_label_name: 'car',
                    object_detection_details: { x: 100, y: 100, width: 200, height: 200 }
                }
            ]
        });
        await tick();

        const canvases = container.querySelectorAll('canvas');
        expect(canvases).toHaveLength(1);
        expect(canvases[0]).toHaveAttribute('width', '300');
        expect(canvases[0]).toHaveAttribute('height', '300');
        const context = canvasContexts.get(canvases[0]);
        expect(context?.strokeRect).toHaveBeenLastCalledWith(30, 30, 60, 60);
    });

    it('does not resize the HTML canvas after transferring it to OffscreenCanvas', async () => {
        const transferredCanvases = new WeakSet<HTMLCanvasElement>();
        const offscreenCanvas = { width: 0, height: 0 } as OffscreenCanvas;
        const widthDescriptor = Object.getOwnPropertyDescriptor(
            HTMLCanvasElement.prototype,
            'width'
        );
        const heightDescriptor = Object.getOwnPropertyDescriptor(
            HTMLCanvasElement.prototype,
            'height'
        );

        vi.spyOn(HTMLCanvasElement.prototype, 'width', 'set').mockImplementation(function (
            this: HTMLCanvasElement,
            value: number
        ) {
            if (transferredCanvases.has(this)) {
                throw new DOMException('Canvas has already been transferred');
            }
            widthDescriptor?.set?.call(this, value);
        });
        vi.spyOn(HTMLCanvasElement.prototype, 'height', 'set').mockImplementation(function (
            this: HTMLCanvasElement,
            value: number
        ) {
            if (transferredCanvases.has(this)) {
                throw new DOMException('Canvas has already been transferred');
            }
            heightDescriptor?.set?.call(this, value);
        });
        Object.defineProperty(HTMLCanvasElement.prototype, 'transferControlToOffscreen', {
            configurable: true,
            value: vi.fn(function (this: HTMLCanvasElement) {
                transferredCanvases.add(this);
                return offscreenCanvas;
            })
        });

        const { container, rerender } = render(AnnotationCanvas, {
            props: {
                sampleId: 'offscreen-resize',
                sourceWidth: 16,
                sourceHeight: 8,
                outputWidth: 8,
                outputHeight: 4,
                annotations: [
                    {
                        annotation_type: 'segmentation_mask',
                        annotation_label_name: 'road',
                        segmentation_mask: [0, 3, 2]
                    }
                ]
            }
        });
        await tick();

        await expect(
            rerender({
                sampleId: 'offscreen-resize',
                sourceWidth: 16,
                sourceHeight: 8,
                outputWidth: 12,
                outputHeight: 6,
                annotations: [
                    {
                        annotation_type: 'segmentation_mask',
                        annotation_label_name: 'road',
                        segmentation_mask: [0, 3, 2]
                    }
                ]
            })
        ).resolves.toBeUndefined();
        await tick();

        const canvas = container.querySelector('canvas');
        expect(canvas).toHaveAttribute('width', '8');
        expect(canvas).toHaveAttribute('height', '4');
        const renderMessages = MockWorker.instances.flatMap((instance) =>
            instance.postMessage.mock.calls
                .map(([message]) => message)
                .filter((message) => message.type === 'render')
        );
        expect(renderMessages.at(-1)).toEqual(
            expect.objectContaining({ outputWidth: 12, outputHeight: 6 })
        );
    });

    it.each([
        {
            name: 'an empty canvas',
            annotations: []
        },
        {
            name: 'a box canvas',
            annotations: [
                {
                    annotation_type: 'object_detection' as const,
                    annotation_label_name: 'car',
                    object_detection_details: { x: 1, y: 1, width: 2, height: 2 }
                }
            ]
        }
    ])('uses the worker fallback when $name later receives a mask', async ({ annotations }) => {
        const transferControlToOffscreen = vi.fn();
        Object.defineProperty(HTMLCanvasElement.prototype, 'transferControlToOffscreen', {
            configurable: true,
            value: transferControlToOffscreen
        });
        const { container, rerender } = render(AnnotationCanvas, {
            props: {
                sampleId: 'main-thread-to-mask',
                sourceWidth: 4,
                sourceHeight: 4,
                outputWidth: 4,
                outputHeight: 4,
                annotations
            }
        });
        await tick();

        await rerender({
            sampleId: 'main-thread-to-mask',
            sourceWidth: 4,
            sourceHeight: 4,
            outputWidth: 4,
            outputHeight: 4,
            annotations: [
                {
                    annotation_type: 'segmentation_mask',
                    annotation_label_name: 'road',
                    segmentation_mask: [0, 4, 12]
                }
            ]
        });
        await tick();

        expect(transferControlToOffscreen).not.toHaveBeenCalled();
        const worker = MockWorker.instances.find((instance) =>
            instance.postMessage.mock.calls.some(([message]) => message.type === 'render')
        );
        const renderMessage = worker?.postMessage.mock.calls
            .map(([message]) => message)
            .find((message) => message.type === 'render');
        expect(worker).toBeDefined();
        expect(worker?.postMessage).not.toHaveBeenCalledWith(
            expect.objectContaining({ type: 'init' }),
            expect.anything()
        );
        expect(worker?.postMessage).toHaveBeenCalledWith(
            expect.objectContaining({ type: 'render', masks: [expect.anything()] })
        );

        worker?.dispatchMessage({
            type: 'image',
            canvasId: renderMessage.canvasId,
            width: 4,
            height: 4,
            data: new Uint8ClampedArray(4 * 4 * 4),
            boxes: []
        });
        const canvas = container.querySelector('canvas');
        expect(canvasContexts.get(canvas as HTMLCanvasElement)?.putImageData).toHaveBeenCalledTimes(
            1
        );
    });

    it('falls back to main-thread painting if OffscreenCanvas transfer is rejected', async () => {
        Object.defineProperty(HTMLCanvasElement.prototype, 'transferControlToOffscreen', {
            configurable: true,
            value: vi.fn(() => {
                throw new DOMException('Canvas has already acquired a rendering context');
            })
        });

        expect(() =>
            render(AnnotationCanvas, {
                props: {
                    sampleId: 'rejected-transfer',
                    sourceWidth: 4,
                    sourceHeight: 4,
                    outputWidth: 4,
                    outputHeight: 4,
                    annotations: [
                        {
                            annotation_type: 'segmentation_mask',
                            annotation_label_name: 'road',
                            segmentation_mask: [0, 4, 12]
                        }
                    ]
                }
            })
        ).not.toThrow();
        await tick();

        const worker = MockWorker.instances.find((instance) =>
            instance.postMessage.mock.calls.some(([message]) => message.type === 'render')
        );
        expect(worker).toBeDefined();
        expect(worker?.postMessage).toHaveBeenCalledWith(
            expect.objectContaining({ type: 'render', masks: [expect.anything()] })
        );
    });

    it('keeps rendering isolated for two canvases with the same sampleId', async () => {
        const first = render(AnnotationCanvas, {
            props: {
                sampleId: 'duplicate-sample-id',
                sourceWidth: 2,
                sourceHeight: 1,
                outputWidth: 2,
                outputHeight: 1,
                annotations: [
                    {
                        annotation_type: 'segmentation_mask',
                        annotation_label_name: 'road',
                        segmentation_mask: [0, 2]
                    }
                ]
            }
        });

        const second = render(AnnotationCanvas, {
            props: {
                sampleId: 'duplicate-sample-id',
                sourceWidth: 2,
                sourceHeight: 1,
                outputWidth: 2,
                outputHeight: 1,
                annotations: [
                    {
                        annotation_type: 'segmentation_mask',
                        annotation_label_name: 'car',
                        segmentation_mask: [0, 2]
                    }
                ]
            }
        });

        await tick();

        expect(MockWorker.instances.length).toBeGreaterThan(0);
        const workersWithRender = MockWorker.instances.filter((instance) =>
            instance.postMessage.mock.calls.some(([message]) => message?.type === 'render')
        );
        expect(workersWithRender.length).toBeGreaterThan(0);

        const renderMessages = workersWithRender
            .flatMap((instance) => instance.postMessage.mock.calls.map(([message]) => message))
            .filter((message) => message?.type === 'render');
        expect(renderMessages).toHaveLength(2);

        const canvasIds = [...new Set(renderMessages.map((message) => message.canvasId))];
        expect(canvasIds).toHaveLength(2);

        const firstCanvas = first.container.querySelector('canvas');
        const secondCanvas = second.container.querySelector('canvas');
        expect(firstCanvas).not.toBeNull();
        expect(secondCanvas).not.toBeNull();

        const firstContext = canvasContexts.get(firstCanvas as HTMLCanvasElement);
        const secondContext = canvasContexts.get(secondCanvas as HTMLCanvasElement);
        expect(firstContext).toBeDefined();
        expect(secondContext).toBeDefined();

        const findWorkerForCanvasId = (canvasId: string): MockWorker | undefined =>
            workersWithRender.find((instance) =>
                instance.postMessage.mock.calls.some(
                    ([message]) => message?.type === 'render' && message.canvasId === canvasId
                )
            );
        const firstWorker = findWorkerForCanvasId(canvasIds[0]);
        const secondWorker = findWorkerForCanvasId(canvasIds[1]);
        expect(firstWorker).toBeDefined();
        expect(secondWorker).toBeDefined();

        firstWorker?.dispatchMessage({
            type: 'image',
            canvasId: canvasIds[0],
            width: 2,
            height: 1,
            data: new Uint8ClampedArray([11, 12, 13, 255, 21, 22, 23, 255]),
            boxes: [],
            stroke: 2
        });

        secondWorker?.dispatchMessage({
            type: 'image',
            canvasId: canvasIds[1],
            width: 2,
            height: 1,
            data: new Uint8ClampedArray([31, 32, 33, 255, 41, 42, 43, 255]),
            boxes: [],
            stroke: 2
        });

        expect(firstContext?.putImageData).toHaveBeenCalledTimes(1);
        expect(secondContext?.putImageData).toHaveBeenCalledTimes(1);

        const firstImageData = firstContext?.putImageData.mock.calls[0][0] as ImageData;
        const secondImageData = secondContext?.putImageData.mock.calls[0][0] as ImageData;
        expect(firstImageData.data).not.toEqual(secondImageData.data);
    });
});
