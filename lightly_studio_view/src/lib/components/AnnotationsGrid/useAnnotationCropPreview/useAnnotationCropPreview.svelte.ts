import { renderCropObjectUrl, type CropWindow } from '../AnnotationItem/renderCropObjectUrl';

/**
 * Drag-to-search crop preview state machine. Tiles report only their crop
 * geometry; the blob is rendered lazily when a drag starts (not per visible
 * tile), and must be revoked by the caller (via `cleanup`) on unmount.
 *
 * Does not call `onDestroy` itself so it stays testable outside a mounted
 * component - the caller wires `onDestroy(cleanup)`.
 */
export function useAnnotationCropPreview() {
    const cropWindowByAnnotationId = $state<Record<string, CropWindow>>({});
    const cropUrlByAnnotationId = $state<Record<string, string>>({});
    // Not `$state`: pure bookkeeping to detect stale renders, never rendered itself.
    const cropRenderGenerationByAnnotationId = new Map<string, number>();

    function revokeCropUrl(annotationId: string) {
        const url = cropUrlByAnnotationId[annotationId];
        if (url) {
            URL.revokeObjectURL(url);
            delete cropUrlByAnnotationId[annotationId];
        }
    }

    // Bumping the generation on every window change and drag start lets a render
    // that resolves late (two drags for the same tile in quick succession) tell
    // it no longer owns the slot, even though window/existence checks alone can't.
    function nextCropRenderGeneration(annotationId: string) {
        const generation = (cropRenderGenerationByAnnotationId.get(annotationId) ?? 0) + 1;
        cropRenderGenerationByAnnotationId.set(annotationId, generation);
        return generation;
    }

    function handleCropWindowChange(annotationId: string, window: CropWindow | null) {
        nextCropRenderGeneration(annotationId);
        if (window) {
            cropWindowByAnnotationId[annotationId] = window;
            return;
        }
        delete cropWindowByAnnotationId[annotationId];
        revokeCropUrl(annotationId);
    }

    async function handleAnnotationDragStart(annotationId: string) {
        const window = cropWindowByAnnotationId[annotationId];
        if (!window) return;
        const generation = nextCropRenderGeneration(annotationId);
        revokeCropUrl(annotationId);
        const url = await renderCropObjectUrl(window, { cancelled: false });
        // Drop the blob if the tile unmounted, or a newer render superseded this one, while rendering.
        if (url && cropRenderGenerationByAnnotationId.get(annotationId) === generation) {
            cropUrlByAnnotationId[annotationId] = url;
        } else if (url) {
            URL.revokeObjectURL(url);
        }
    }

    function cleanup() {
        for (const url of Object.values(cropUrlByAnnotationId)) {
            URL.revokeObjectURL(url);
        }
    }

    return {
        get cropWindowByAnnotationId() {
            return cropWindowByAnnotationId;
        },
        get cropUrlByAnnotationId() {
            return cropUrlByAnnotationId;
        },
        handleCropWindowChange,
        handleAnnotationDragStart,
        cleanup
    };
}
