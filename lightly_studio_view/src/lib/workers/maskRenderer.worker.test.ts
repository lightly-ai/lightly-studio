import { afterEach, describe, expect, it, vi } from 'vitest';
import { createWorkerRenderMessage } from './maskRenderer.testFixtures';

class MockImageData {
    constructor(
        public data: Uint8ClampedArray,
        public width: number,
        public height: number
    ) {}
}

describe('maskRenderer worker', () => {
    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
        vi.resetModules();
    });

    it('resizes the worker-owned OffscreenCanvas when output dimensions change', async () => {
        const canvas = { width: 0, height: 0 };
        const context = {
            canvas,
            clearRect: vi.fn(),
            putImageData: vi.fn(),
            save: vi.fn(),
            restore: vi.fn(),
            lineWidth: 1,
            strokeStyle: '',
            strokeRect: vi.fn()
        };
        const offscreenCanvas = {
            ...canvas,
            getContext: vi.fn(() => context)
        };
        vi.stubGlobal('ImageData', MockImageData as unknown as typeof ImageData);

        await import('./maskRenderer.worker');
        self.onmessage?.(
            new MessageEvent('message', {
                data: { type: 'init', canvasId: 'canvas-1', canvas: offscreenCanvas }
            })
        );
        self.onmessage?.(
            new MessageEvent('message', {
                data: createWorkerRenderMessage()
            })
        );
        self.onmessage?.(
            new MessageEvent('message', {
                data: createWorkerRenderMessage({ outputWidth: 12, outputHeight: 6 })
            })
        );

        expect(context.canvas).toMatchObject({ width: 12, height: 6 });
        expect(context.clearRect).toHaveBeenLastCalledWith(0, 0, 12, 6);
        expect(context.putImageData).toHaveBeenCalledTimes(2);
    });
});
