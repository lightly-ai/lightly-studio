import { createBrushDrawer } from './brushDrawer';
import { createPreviewRenderer } from './previewRenderer';
import { createCanvasMaskManager } from './canvasMaskManager';
import type { SchedulePreviewComposeParams, UseInstanceSegmentationPreviewParams } from './types';

export function useInstanceSegmentationPreview({
    onPreviewVisibilityChange
}: UseInstanceSegmentationPreviewParams = {}) {
    const canvasMaskManager = createCanvasMaskManager();
    const previewRenderer = createPreviewRenderer({ onPreviewVisibilityChange });
    const brushDrawer = createBrushDrawer({
        ensureSourceMaskContext: canvasMaskManager.ensureCanvasMaskContext
    });

    let previewRenderFrameId: number | null = null;

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

            canvasMaskManager.ensureCanvasMaskContext(width, height);
            previewRenderer.composePreviewFromSourceMask(
                canvasMaskManager.getCanvasMaskCanvas(),
                color
            );
        });
    };

    const destroy = () => {
        cancelScheduledPreviewCompose();
        previewRenderer.destroy();
        canvasMaskManager.destroy();
    };

    return {
        setPreviewCanvas: previewRenderer.setPreviewCanvas,
        clearPreview: previewRenderer.clearPreview,
        drawMaskToCanvas: canvasMaskManager.drawMaskToCanvas,
        drawBrushDot: brushDrawer.drawBrushDot,
        drawBrushLine: brushDrawer.drawBrushLine,
        toBinaryMaskFromCanvas: canvasMaskManager.toBinaryMaskFromCanvas,
        schedulePreviewCompose,
        cancelScheduledPreviewCompose,
        destroy
    };
}
