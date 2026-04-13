import { createBrushDrawer } from './BrushDrawer';
import { createPreviewRenderer } from './PreviewRenderer';
import { createSourceMaskManager } from './SourceMaskManager';
import type { SchedulePreviewComposeParams, UseInstanceSegmentationPreviewParams } from './types';

export function useInstanceSegmentationPreview({
    onPreviewVisibilityChange
}: UseInstanceSegmentationPreviewParams = {}) {
    const sourceMaskManager = createSourceMaskManager();
    const previewRenderer = createPreviewRenderer({ onPreviewVisibilityChange });
    const brushDrawer = createBrushDrawer({
        ensureSourceMaskContext: sourceMaskManager.ensureSourceMaskContext
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

            sourceMaskManager.ensureSourceMaskContext(width, height);
            previewRenderer.composePreviewFromSourceMask(
                sourceMaskManager.getSourceMaskCanvas(),
                color
            );
        });
    };

    const destroy = () => {
        cancelScheduledPreviewCompose();
        previewRenderer.destroy();
        sourceMaskManager.destroy();
    };

    return {
        setPreviewCanvas: previewRenderer.setPreviewCanvas,
        clearPreview: previewRenderer.clearPreview,
        drawMaskToSourceCanvas: sourceMaskManager.drawMaskToSourceCanvas,
        drawBrushDot: brushDrawer.drawBrushDot,
        drawBrushLine: brushDrawer.drawBrushLine,
        toBinaryMaskFromSourceCanvas: sourceMaskManager.toBinaryMaskFromSourceCanvas,
        schedulePreviewCompose,
        cancelScheduledPreviewCompose,
        destroy
    };
}
