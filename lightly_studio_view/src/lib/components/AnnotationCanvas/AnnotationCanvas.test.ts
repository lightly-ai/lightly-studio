import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { tick } from 'svelte';
import AnnotationCanvas from './AnnotationCanvas.svelte';

vi.mock('$lib/utils', () => ({
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

class MockResizeObserver {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
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
        vi.stubGlobal('ResizeObserver', MockResizeObserver as unknown as typeof ResizeObserver);
        vi.stubGlobal('ImageData', MockImageData as unknown as typeof ImageData);
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    afterEach(async () => {
        const { shutdownMaskRendererPool } = await import('$lib/workers/maskRendererPool');
        shutdownMaskRendererPool();
    });

    it('draws object-detection boxes on fallback canvas when there are no masks', async () => {
        const { container } = render(AnnotationCanvas, {
            props: {
                sampleId: 'sample-object-detection',
                width: 100,
                height: 100,
                annotations: [
                    {
                        annotation_type: 'object_detection',
                        annotation_label_name: 'car',
                        object_detection_details: { x: 10.2, y: 20.6, width: 30.4, height: 40.9 }
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
        expect(context?.clearRect).toHaveBeenCalledWith(0, 0, 100, 100);
        expect(context?.strokeRect).toHaveBeenCalledWith(10, 21, 30, 41);
    });

    it('posts a worker render message when masks are present', async () => {
        render(AnnotationCanvas, {
            props: {
                sampleId: 'sample-masks',
                width: 16,
                height: 8,
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
        expect(context?.clearRect).toHaveBeenCalledWith(0, 0, 16, 8);
        expect(worker.postMessage).toHaveBeenCalledTimes(1);
        expect(worker.postMessage).toHaveBeenCalledWith(
            expect.objectContaining({
                type: 'render',
                width: 16,
                height: 8,
                scaleX: 0,
                scaleY: 0,
                boxes: [],
                masks: [expect.objectContaining({ rle: [0, 3, 2] })]
            })
        );
    });

    it('clears and exits early when there are no drawable annotations', async () => {
        const { container } = render(AnnotationCanvas, {
            props: { sampleId: 'sample-empty', width: 64, height: 32, annotations: [] }
        });

        await tick();
        const canvas = container.querySelector('canvas');
        expect(canvas).not.toBeNull();
        const context = canvasContexts.get(canvas as HTMLCanvasElement);
        expect(context).toBeDefined();

        expect(MockWorker.instances).toHaveLength(0);
        expect(context?.clearRect).toHaveBeenCalledWith(0, 0, 64, 32);
        expect(context?.strokeRect).not.toHaveBeenCalled();
    });

    it('keeps rendering isolated for two canvases with the same sampleId', async () => {
        const first = render(AnnotationCanvas, {
            props: {
                sampleId: 'duplicate-sample-id',
                width: 2,
                height: 1,
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
                width: 2,
                height: 1,
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
