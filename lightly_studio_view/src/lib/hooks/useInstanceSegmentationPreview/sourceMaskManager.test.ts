import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createSourceMaskManager } from './sourceMaskManager';

type Mock2dContext = {
    clearRect: ReturnType<typeof vi.fn>;
    createImageData: ReturnType<typeof vi.fn>;
    putImageData: ReturnType<typeof vi.fn>;
    getImageData: ReturnType<typeof vi.fn>;
};

describe('createSourceMaskManager', () => {
    let sourceContext: Mock2dContext;

    beforeEach(() => {
        sourceContext = {
            clearRect: vi.fn(),
            createImageData: vi.fn((width: number, height: number) => ({
                data: new Uint8ClampedArray(width * height * 4),
                width,
                height
            })),
            putImageData: vi.fn(),
            getImageData: vi.fn(() => ({
                data: new Uint8ClampedArray(2 * 2 * 4),
                width: 2,
                height: 2
            }))
        };

        vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(
            (contextId: string) => {
                if (contextId !== '2d') return null;
                return sourceContext as unknown as CanvasRenderingContext2D;
            }
        );
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('draws a binary mask into the source canvas alpha channel', () => {
        const manager = createSourceMaskManager();

        manager.drawMaskToSourceCanvas(new Uint8Array([0, 1, 0, 1]), 2, 2);

        expect(sourceContext.createImageData).toHaveBeenCalledWith(2, 2);
        expect(sourceContext.putImageData).toHaveBeenCalledTimes(1);

        const imageData = sourceContext.putImageData.mock.calls[0][0] as ImageData;
        expect(imageData.data[3]).toBe(0);
        expect(imageData.data[7]).toBe(255);
        expect(imageData.data[11]).toBe(0);
        expect(imageData.data[15]).toBe(255);
    });

    it('extracts binary mask from source canvas alpha channel', () => {
        sourceContext.getImageData.mockReturnValue({
            data: new Uint8ClampedArray([0, 0, 0, 0, 0, 0, 0, 255, 0, 0, 0, 0, 0, 0, 0, 255]),
            width: 2,
            height: 2
        });

        const manager = createSourceMaskManager();
        manager.drawMaskToSourceCanvas(null, 2, 2);

        const mask = manager.toBinaryMaskFromSourceCanvas(2, 2);

        expect(mask).not.toBeNull();
        expect(Array.from(mask ?? [])).toEqual([0, 1, 0, 1]);
    });

    it('recreates the source mask canvas when dimensions change', () => {
        const createElementSpy = vi.spyOn(document, 'createElement');
        const manager = createSourceMaskManager();

        manager.drawMaskToSourceCanvas(null, 2, 2);
        manager.drawMaskToSourceCanvas(null, 3, 3);

        const createdCanvasCount = createElementSpy.mock.calls.filter(
            (call) => call[0] === 'canvas'
        ).length;

        expect(createdCanvasCount).toBe(2);
    });
});
