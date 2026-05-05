interface CanvasMaskManager {
    ensureCanvasMaskContext: (width: number, height: number) => CanvasRenderingContext2D | null;
    drawMaskToCanvas: (mask: Uint8Array | null, width: number, height: number) => void;
    toBinaryMaskFromCanvas: (width: number, height: number) => Uint8Array | null;
    getCanvasMaskCanvas: () => HTMLCanvasElement | null;
    destroy: () => void;
}

export function createCanvasMaskManager(): CanvasMaskManager {
    let canvasMaskCanvas: HTMLCanvasElement | null = null;
    let canvasMaskContext: CanvasRenderingContext2D | null = null;

    const ensureCanvasMaskContext = (width: number, height: number) => {
        if (typeof document === 'undefined') return null;

        if (
            !canvasMaskCanvas ||
            canvasMaskCanvas.width !== width ||
            canvasMaskCanvas.height !== height
        ) {
            // Recreate when image size changes.
            canvasMaskCanvas = document.createElement('canvas');
            canvasMaskCanvas.width = width;
            canvasMaskCanvas.height = height;
            canvasMaskContext = null;
        }

        if (canvasMaskContext) return canvasMaskContext;

        canvasMaskContext = canvasMaskCanvas.getContext('2d');
        return canvasMaskContext;
    };

    const drawMaskToCanvas = (mask: Uint8Array | null, width: number, height: number) => {
        const canvasContext = ensureCanvasMaskContext(width, height);
        if (!canvasContext || !canvasMaskCanvas) return;

        canvasContext.clearRect(0, 0, canvasMaskCanvas.width, canvasMaskCanvas.height);
        if (!mask) return;

        // Encode binary mask as alpha-only pixels.
        const imageData = canvasContext.createImageData(width, height);
        const pixels = imageData.data;

        for (let i = 0; i < mask.length; i++) {
            if (mask[i] !== 1) continue;
            pixels[i * 4 + 3] = 255; // +3 selects alpha in RGBA.
        }

        canvasContext.putImageData(imageData, 0, 0);
    };

    const toBinaryMaskFromCanvas = (width: number, height: number) => {
        const context = ensureCanvasMaskContext(width, height);
        if (!context || !canvasMaskCanvas) return null;

        const imageData = context.getImageData(
            0,
            0,
            canvasMaskCanvas.width,
            canvasMaskCanvas.height
        );
        const binaryMask = new Uint8Array(canvasMaskCanvas.width * canvasMaskCanvas.height);
        const pixels = imageData.data;

        // Any non-zero alpha is a foreground mask pixel.
        for (let i = 0; i < binaryMask.length; i++) {
            binaryMask[i] = pixels[i * 4 + 3] > 0 ? 1 : 0;
        }

        return binaryMask;
    };

    const getCanvasMaskCanvas = () => canvasMaskCanvas;

    const destroy = () => {
        canvasMaskCanvas = null;
        canvasMaskContext = null;
    };

    return {
        ensureCanvasMaskContext,
        drawMaskToCanvas,
        toBinaryMaskFromCanvas,
        getCanvasMaskCanvas,
        destroy
    };
}
