import type { ParsedColor } from './types';

interface PreviewRendererParams {
    onPreviewVisibilityChange?: (visible: boolean) => void;
}

export interface PreviewRenderer {
    setPreviewCanvas: (canvas: HTMLCanvasElement | null) => void;
    clearPreview: () => void;
    composePreviewFromSourceMask: (
        sourceMaskCanvas: HTMLCanvasElement | null,
        color: ParsedColor
    ) => void;
    destroy: () => void;
}

export function createPreviewRenderer({ onPreviewVisibilityChange }: PreviewRendererParams = {}) {
    let previewCanvas: HTMLCanvasElement | null = null;
    let previewCanvasContext: CanvasRenderingContext2D | null = null;

    const setPreviewVisibility = (visible: boolean) => {
        onPreviewVisibilityChange?.(visible);
    };

    const setPreviewCanvas = (canvas: HTMLCanvasElement | null) => {
        if (previewCanvas === canvas) return;

        previewCanvas = canvas;
        previewCanvasContext = null;
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

    const composePreviewFromSourceMask = (
        sourceMaskCanvas: HTMLCanvasElement | null,
        color: ParsedColor
    ) => {
        const previewContext = ensurePreviewCanvasContext();
        if (!sourceMaskCanvas || !previewContext || !previewCanvas) return;

        previewContext.clearRect(0, 0, previewCanvas.width, previewCanvas.height);
        previewContext.drawImage(sourceMaskCanvas, 0, 0);
        // Keep only mask alpha, then tint it.
        previewContext.globalCompositeOperation = 'source-in';
        previewContext.fillStyle = `rgba(${color.r}, ${color.g}, ${color.b}, ${color.a / 255})`;
        previewContext.fillRect(0, 0, previewCanvas.width, previewCanvas.height);
        previewContext.globalCompositeOperation = 'source-over';

        setPreviewVisibility(true);
    };

    const destroy = () => {
        previewCanvas = null;
        previewCanvasContext = null;
    };

    return {
        setPreviewCanvas,
        clearPreview,
        composePreviewFromSourceMask,
        destroy
    } satisfies PreviewRenderer;
}
