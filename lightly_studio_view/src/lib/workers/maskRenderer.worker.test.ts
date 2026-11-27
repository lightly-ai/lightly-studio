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
            strokeRect: vi.fn(),
            fillStyle: '',
            beginPath: vi.fn(),
            moveTo: vi.fn(),
            lineTo: vi.fn(),
            closePath: vi.fn(),
            rect: vi.fn(),
            clip: vi.fn(),
            fill: vi.fn(),
            stroke: vi.fn()
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

    it('draws polygons after masks on the worker-owned canvas', async () => {
        const context = {
            canvas: { width: 0, height: 0 },
            clearRect: vi.fn(),
            putImageData: vi.fn(),
            save: vi.fn(),
            restore: vi.fn(),
            lineWidth: 1,
            strokeStyle: '',
            fillStyle: '',
            strokeRect: vi.fn(),
            beginPath: vi.fn(),
            moveTo: vi.fn(),
            lineTo: vi.fn(),
            closePath: vi.fn(),
            rect: vi.fn(),
            clip: vi.fn(),
            fill: vi.fn(),
            stroke: vi.fn()
        };
        vi.stubGlobal('ImageData', MockImageData as unknown as typeof ImageData);

        await import('./maskRenderer.worker');
        self.onmessage?.(
            new MessageEvent('message', {
                data: {
                    type: 'init',
                    canvasId: 'canvas-1',
                    canvas: { getContext: vi.fn(() => context) }
                }
            })
        );
        self.onmessage?.(
            new MessageEvent('message', {
                data: createWorkerRenderMessage({
                    polygons: [
                        {
                            parts: [
                                [
                                    [0, 0],
                                    [16, 0],
                                    [16, 8]
                                ]
                            ],
                            strokeColor: [255, 0, 0, 255],
                            fillColor: [255, 0, 0, 102]
                        }
                    ]
                })
            })
        );

        expect(context.moveTo).toHaveBeenCalledWith(0, 0);
        expect(context.lineTo).toHaveBeenCalledWith(8, 0);
        expect(context.lineTo).toHaveBeenCalledWith(8, 4);
        expect(context.putImageData.mock.invocationCallOrder[0]).toBeLessThan(
            context.fill.mock.invocationCallOrder[0]
        );
    });

    it('posts transformed polygons in the fallback image message', async () => {
        const postMessage = vi.fn();
        vi.stubGlobal('postMessage', postMessage);

        await import('./maskRenderer.worker');
        self.onmessage?.(
            new MessageEvent('message', {
                data: createWorkerRenderMessage({
                    polygons: [
                        {
                            parts: [
                                [
                                    [0, 0],
                                    [16, 0],
                                    [16, 8]
                                ]
                            ],
                            strokeColor: [255, 0, 0, 255],
                            fillColor: [255, 0, 0, 102]
                        }
                    ]
                })
            })
        );

        expect(postMessage).toHaveBeenCalledWith(
            expect.objectContaining({
                type: 'image',
                polygonClipRect: { x: 0, y: 0, width: 8, height: 4 },
                polygons: [
                    expect.objectContaining({
                        parts: [
                            [
                                [0, 0],
                                [8, 0],
                                [8, 4]
                            ]
                        ]
                    })
                ]
            }),
            expect.anything()
        );
    });
});
