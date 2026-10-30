import { afterEach, describe, expect, it, vi } from 'vitest';

afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    vi.resetModules();
});

describe('camera RGB worker', () => {
    it('decodes a Blob in the worker, closes the bitmap, and transfers the colors', async () => {
        const blob = new Blob(['image']);
        const pixels = new Uint8ClampedArray([255, 0, 0, 255]);
        const bitmap = { width: 1, height: 1, close: vi.fn() };
        const context = {
            drawImage: vi.fn(),
            getImageData: vi.fn(() => ({ width: 1, height: 1, data: pixels }))
        };
        const createBitmap = vi.fn(async () => bitmap);
        vi.stubGlobal('createImageBitmap', createBitmap);
        vi.stubGlobal(
            'OffscreenCanvas',
            class {
                width = 1;
                height = 1;
                getContext() {
                    return context;
                }
            }
        );
        const postMessage = vi.spyOn(self, 'postMessage').mockImplementation(() => undefined);

        await import('./cameraRgbWorker');
        const camera = {
            sceneToCamera: new Float64Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0]),
            cameraMatrix: new Float64Array([1, 0, 0, 0, 1, 0, 0, 0, 1]),
            projWidth: 1,
            projHeight: 1,
            blob
        };
        const message = {
            id: 1,
            positions: new Float32Array([0, 0, 1]),
            count: 1,
            cameras: [camera]
        };
        await self.onmessage?.(new MessageEvent('message', { data: message }));

        expect(createBitmap).toHaveBeenCalledWith(blob);
        expect(context.drawImage).toHaveBeenCalledWith(bitmap, 0, 0);
        expect(bitmap.close).toHaveBeenCalledOnce();
        expect(postMessage).toHaveBeenCalledWith({ id: 1, colors: new Float32Array([1, 0, 0]) }, [
            expect.any(ArrayBuffer)
        ]);

        await self.onmessage?.(new MessageEvent('message', { data: message }));
        expect(createBitmap).toHaveBeenCalledTimes(2);
    });

    it('keeps only the newest queued request while a decode is running', async () => {
        let finishDecode: ((bitmap: object) => void) | undefined;
        const bitmap = { width: 1, height: 1, close: vi.fn() };
        const createBitmap = vi.fn(
            () =>
                new Promise<object>((resolve) => {
                    finishDecode = resolve;
                })
        );
        vi.stubGlobal('createImageBitmap', createBitmap);
        vi.stubGlobal(
            'OffscreenCanvas',
            class {
                width = 1;
                height = 1;
                getContext() {
                    return {
                        drawImage: vi.fn(),
                        getImageData: () => ({
                            width: 1,
                            height: 1,
                            data: new Uint8ClampedArray(4)
                        })
                    };
                }
            }
        );
        const postMessage = vi.spyOn(self, 'postMessage').mockImplementation(() => undefined);
        await import('./cameraRgbWorker');

        const input = (id: number) => ({
            id,
            positions: new Float32Array(0),
            count: 0,
            cameras: [
                {
                    sceneToCamera: new Float64Array(12),
                    cameraMatrix: new Float64Array(9),
                    projWidth: 1,
                    projHeight: 1,
                    blob: new Blob()
                }
            ]
        });
        const send = (id: number) =>
            self.onmessage?.(new MessageEvent('message', { data: input(id) }));
        void send(1);
        void send(2);
        void send(3);
        expect(postMessage).toHaveBeenCalledWith({ id: 2, cancelled: true });
        expect(createBitmap).toHaveBeenCalledTimes(1);

        finishDecode?.(bitmap);
        await vi.waitFor(() => expect(createBitmap).toHaveBeenCalledTimes(2));
        finishDecode?.(bitmap);
        await vi.waitFor(() => expect(postMessage).toHaveBeenCalledTimes(3));
        expect(postMessage.mock.calls.map(([result]) => result.id)).toEqual([2, 1, 3]);
        expect(postMessage).toHaveBeenCalledWith({ id: 1, cancelled: true });
    });
});
