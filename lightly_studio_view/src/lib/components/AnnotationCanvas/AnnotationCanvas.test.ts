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
    terminate = vi.fn();

    constructor() {
        MockWorker.instances.push(this);
    }
}

class MockResizeObserver {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
}

describe('AnnotationCanvas', () => {
    let mockContext: Mock2dContext;

    beforeEach(() => {
        MockWorker.instances = [];

        mockContext = {
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
        };

        vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(
            (contextId: string) => {
                if (contextId !== '2d') {
                    return null;
                }
                return mockContext as unknown as CanvasRenderingContext2D;
            }
        );

        vi.stubGlobal('Worker', MockWorker as unknown as typeof Worker);
        vi.stubGlobal('ResizeObserver', MockResizeObserver as unknown as typeof ResizeObserver);
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('draws object-detection boxes on fallback canvas when there are no masks', async () => {
        render(AnnotationCanvas, {
            props: {
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

        expect(MockWorker.instances).toHaveLength(0);
        expect(mockContext.clearRect).toHaveBeenCalledWith(0, 0, 100, 100);
        expect(mockContext.strokeRect).toHaveBeenCalledWith(10, 21, 30, 41);
    });

    it('posts a worker render message when masks are present', async () => {
        render(AnnotationCanvas, {
            props: {
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

        expect(MockWorker.instances).toHaveLength(1);
        const worker = MockWorker.instances[0];
        expect(mockContext.clearRect).toHaveBeenCalledWith(0, 0, 16, 8);
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
        render(AnnotationCanvas, { props: { width: 64, height: 32, annotations: [] } });

        await tick();

        expect(MockWorker.instances).toHaveLength(0);
        expect(mockContext.clearRect).toHaveBeenCalledWith(0, 0, 64, 32);
        expect(mockContext.strokeRect).not.toHaveBeenCalled();
    });
});
