import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createPreviewRenderer } from './PreviewRenderer';

type Mock2dContext = {
    clearRect: ReturnType<typeof vi.fn>;
    drawImage: ReturnType<typeof vi.fn>;
    fillRect: ReturnType<typeof vi.fn>;
    globalCompositeOperation: string;
    fillStyle: string;
};

describe('createPreviewRenderer', () => {
    let previewCanvas: HTMLCanvasElement;
    let sourceMaskCanvas: HTMLCanvasElement;
    let previewContext: Mock2dContext;

    beforeEach(() => {
        previewCanvas = document.createElement('canvas');
        previewCanvas.width = 2;
        previewCanvas.height = 2;

        sourceMaskCanvas = document.createElement('canvas');

        previewContext = {
            clearRect: vi.fn(),
            drawImage: vi.fn(),
            fillRect: vi.fn(),
            globalCompositeOperation: 'source-over',
            fillStyle: 'black'
        };

        vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(function (
            this: HTMLCanvasElement,
            contextId: string
        ) {
            if (contextId !== '2d') return null;
            if (this !== previewCanvas) return null;

            return previewContext as unknown as CanvasRenderingContext2D;
        });
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('composes a tinted preview from the source mask canvas', () => {
        const onPreviewVisibilityChange = vi.fn();
        const renderer = createPreviewRenderer({ onPreviewVisibilityChange });

        renderer.setPreviewCanvas(previewCanvas);
        renderer.composePreviewFromSourceMask(sourceMaskCanvas, {
            r: 0,
            g: 64,
            b: 255,
            a: 128
        });

        expect(previewContext.clearRect).toHaveBeenCalledWith(0, 0, 2, 2);
        expect(previewContext.drawImage).toHaveBeenCalledWith(sourceMaskCanvas, 0, 0);
        expect(previewContext.fillRect).toHaveBeenCalledWith(0, 0, 2, 2);
        expect(previewContext.fillStyle).toBe(`rgba(0, 64, 255, ${128 / 255})`);
        expect(previewContext.globalCompositeOperation).toBe('source-over');
        expect(onPreviewVisibilityChange).toHaveBeenCalledWith(true);
    });

    it('clears the preview and marks it as hidden', () => {
        const onPreviewVisibilityChange = vi.fn();
        const renderer = createPreviewRenderer({ onPreviewVisibilityChange });

        renderer.setPreviewCanvas(previewCanvas);
        renderer.clearPreview();

        expect(previewContext.clearRect).toHaveBeenCalledWith(0, 0, 2, 2);
        expect(onPreviewVisibilityChange).toHaveBeenCalledWith(false);
    });
});
