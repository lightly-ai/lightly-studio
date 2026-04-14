export interface SourceMaskManager {
    ensureSourceMaskContext: (width: number, height: number) => CanvasRenderingContext2D | null;
    drawMaskToSourceCanvas: (mask: Uint8Array | null, width: number, height: number) => void;
    toBinaryMaskFromSourceCanvas: (width: number, height: number) => Uint8Array | null;
    getSourceMaskCanvas: () => HTMLCanvasElement | null;
    destroy: () => void;
}

export function createSourceMaskManager(): SourceMaskManager {
    let sourceMaskCanvas: HTMLCanvasElement | null = null;
    let sourceMaskContext: CanvasRenderingContext2D | null = null;

    const ensureSourceMaskContext = (width: number, height: number) => {
        if (typeof document === 'undefined') return null;

        if (
            !sourceMaskCanvas ||
            sourceMaskCanvas.width !== width ||
            sourceMaskCanvas.height !== height
        ) {
            // Recreate when image size changes.
            sourceMaskCanvas = document.createElement('canvas');
            sourceMaskCanvas.width = width;
            sourceMaskCanvas.height = height;
            sourceMaskContext = null;
        }

        if (sourceMaskContext) return sourceMaskContext;

        sourceMaskContext = sourceMaskCanvas.getContext('2d');
        return sourceMaskContext;
    };

    const drawMaskToSourceCanvas = (mask: Uint8Array | null, width: number, height: number) => {
        const sourceContext = ensureSourceMaskContext(width, height);
        if (!sourceContext || !sourceMaskCanvas) return;

        sourceContext.clearRect(0, 0, sourceMaskCanvas.width, sourceMaskCanvas.height);
        if (!mask) return;

        // Encode binary mask as alpha-only pixels.
        const imageData = sourceContext.createImageData(width, height);
        const pixels = imageData.data;

        for (let i = 0; i < mask.length; i++) {
            if (mask[i] !== 1) continue;
            pixels[i * 4 + 3] = 255; // +3 selects alpha in RGBA.
        }

        sourceContext.putImageData(imageData, 0, 0);
    };

    const toBinaryMaskFromSourceCanvas = (width: number, height: number) => {
        const context = ensureSourceMaskContext(width, height);
        if (!context || !sourceMaskCanvas) return null;

        const imageData = context.getImageData(
            0,
            0,
            sourceMaskCanvas.width,
            sourceMaskCanvas.height
        );
        const binaryMask = new Uint8Array(sourceMaskCanvas.width * sourceMaskCanvas.height);
        const pixels = imageData.data;

        // Any non-zero alpha is a foreground mask pixel.
        for (let i = 0; i < binaryMask.length; i++) {
            binaryMask[i] = pixels[i * 4 + 3] > 0 ? 1 : 0;
        }

        return binaryMask;
    };

    const getSourceMaskCanvas = () => sourceMaskCanvas;

    const destroy = () => {
        sourceMaskCanvas = null;
        sourceMaskContext = null;
    };

    return {
        ensureSourceMaskContext,
        drawMaskToSourceCanvas,
        toBinaryMaskFromSourceCanvas,
        getSourceMaskCanvas,
        destroy
    };
}
