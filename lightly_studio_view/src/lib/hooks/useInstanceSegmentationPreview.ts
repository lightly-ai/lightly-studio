type BrushPoint = { x: number; y: number };
type ParsedColor = { r: number; g: number; b: number; a: number };

type UseInstanceSegmentationPreviewParams = {
    onPreviewVisibilityChange?: (visible: boolean) => void;
};

type SchedulePreviewComposeParams = {
    width: number;
    height: number;
    color: ParsedColor;
    isDrawing: boolean;
};

export function useInstanceSegmentationPreview({
    onPreviewVisibilityChange
}: UseInstanceSegmentationPreviewParams = {}) {
    // Colorized canvas shown in the UI.
    let previewCanvas: HTMLCanvasElement | null = null;
    let previewCanvasContext: CanvasRenderingContext2D | null = null;
    // Binary alpha mask used as the drawing source of truth.
    let sourceMaskCanvas: HTMLCanvasElement | null = null;
    let sourceMaskContext: CanvasRenderingContext2D | null = null;
    let previewRenderFrameId: number | null = null;

    const setPreviewVisibility = (visible: boolean) => {
        onPreviewVisibilityChange?.(visible);
    };

    const setPreviewCanvas = (canvas: HTMLCanvasElement | null) => {
        if (previewCanvas === canvas) return;
        previewCanvas = canvas;
        previewCanvasContext = null;
    };

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

    const ensurePreviewCanvasContext = () => {
        if (!previewCanvas) return null;
        if (previewCanvasContext) return previewCanvasContext;

        previewCanvasContext = previewCanvas.getContext('2d');
        return previewCanvasContext;
    };

    const clearPreview = () => {
        const context = ensurePreviewCanvasContext();
        if (!context || !previewCanvas) return;

        context.clearRect(0, 0, previewCanvas.width, previewCanvas.height);
        setPreviewVisibility(false);
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

    const composePreviewFromSourceMask = (color: ParsedColor) => {
        const source = sourceMaskCanvas;
        const previewContext = ensurePreviewCanvasContext();
        if (!source || !previewContext || !previewCanvas) return;

        previewContext.clearRect(0, 0, previewCanvas.width, previewCanvas.height);
        previewContext.drawImage(source, 0, 0);
        // Keep only mask alpha, then tint it.
        previewContext.globalCompositeOperation = 'source-in';
        previewContext.fillStyle = `rgba(${color.r}, ${color.g}, ${color.b}, ${color.a / 255})`;
        previewContext.fillRect(0, 0, previewCanvas.width, previewCanvas.height);
        previewContext.globalCompositeOperation = 'source-over';

        setPreviewVisibility(true);
    };

    const drawBrushDot = ({
        point,
        brushRadius,
        width,
        height
    }: {
        point: BrushPoint;
        brushRadius: number;
        width: number;
        height: number;
    }) => {
        const context = ensureSourceMaskContext(width, height);
        if (!context) return;

        context.globalCompositeOperation = 'source-over';
        context.fillStyle = 'black';
        context.beginPath();
        context.arc(point.x, point.y, brushRadius, 0, Math.PI * 2);
        context.fill();
    };

    const drawBrushLine = ({
        from,
        to,
        brushRadius,
        width,
        height
    }: {
        from: BrushPoint;
        to: BrushPoint;
        brushRadius: number;
        width: number;
        height: number;
    }) => {
        const context = ensureSourceMaskContext(width, height);
        if (!context) return;

        context.globalCompositeOperation = 'source-over';
        context.strokeStyle = 'black';
        context.lineWidth = brushRadius * 2;
        context.lineCap = 'round';
        context.lineJoin = 'round';
        context.beginPath();
        context.moveTo(from.x, from.y);
        context.lineTo(to.x, to.y);
        context.stroke();
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

    const cancelScheduledPreviewCompose = () => {
        if (previewRenderFrameId === null) return;

        cancelAnimationFrame(previewRenderFrameId);
        previewRenderFrameId = null;
    };

    const schedulePreviewCompose = ({
        width,
        height,
        color,
        isDrawing
    }: SchedulePreviewComposeParams) => {
        // Coalesce multiple pointer moves into one frame.
        if (previewRenderFrameId !== null) return;

        previewRenderFrameId = requestAnimationFrame(() => {
            previewRenderFrameId = null;
            if (!isDrawing) return;

            ensureSourceMaskContext(width, height);
            composePreviewFromSourceMask(color);
        });
    };

    const destroy = () => {
        cancelScheduledPreviewCompose();
        previewCanvas = null;
        previewCanvasContext = null;
        sourceMaskCanvas = null;
        sourceMaskContext = null;
    };

    return {
        setPreviewCanvas,
        clearPreview,
        drawMaskToSourceCanvas,
        drawBrushDot,
        drawBrushLine,
        toBinaryMaskFromSourceCanvas,
        schedulePreviewCompose,
        cancelScheduledPreviewCompose,
        destroy
    };
}
