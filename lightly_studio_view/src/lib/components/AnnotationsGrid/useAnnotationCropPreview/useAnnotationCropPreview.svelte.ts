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

    function revokeCropUrl(annotationId: string) {
        const url = cropUrlByAnnotationId[annotationId];
        if (url) {
            URL.revokeObjectURL(url);
            delete cropUrlByAnnotationId[annotationId];
        }
    }

    function handleCropWindowChange(annotationId: string, window: CropWindow | null) {
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
        revokeCropUrl(annotationId);
        const url = await renderCropObjectUrl(window, { cancelled: false });
        // The tile may have unmounted while rendering; drop the blob if so.
        if (url && cropWindowByAnnotationId[annotationId]) {
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
