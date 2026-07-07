/** Geometry of the padded-bbox crop window, in original-image pixel coordinates. */
export type CropWindow = {
    sourceUrl: string;
    sampleWidth: number;
    sampleHeight: number;
    windowWidth: number;
    windowHeight: number;
    windowX: number;
    windowY: number;
};

/** Mutable flag the caller flips to abort the async render (e.g. effect cleanup). */
type CancelToken = { cancelled: boolean };

/**
 * Render the crop window of `sourceUrl` into a canvas and return a blob object URL.
 *
 * Used as the drag-to-search preview for an annotation crop: it is generated
 * lazily when a drag begins, not eagerly per visible tile. Resolves to `null`
 * if the render was cancelled or the image/canvas is unavailable. The caller
 * owns the returned URL and must revoke it with `URL.revokeObjectURL`.
 */
export function renderCropObjectUrl(win: CropWindow, token: CancelToken): Promise<string | null> {
    return new Promise((resolve) => {
        const imageElement = new Image();
        // The thumbnail may be served cross-origin (dev server); without this the
        // canvas would be tainted and toBlob would throw.
        imageElement.crossOrigin = 'anonymous';
        imageElement.onload = () => {
            if (token.cancelled) return resolve(null);
            // The thumbnail can be downscaled relative to the original image size the
            // crop geometry is expressed in.
            const resolutionX = imageElement.naturalWidth / win.sampleWidth;
            const resolutionY = imageElement.naturalHeight / win.sampleHeight;
            const canvas = document.createElement('canvas');
            canvas.width = Math.max(1, Math.round(win.windowWidth * resolutionX));
            canvas.height = Math.max(1, Math.round(win.windowHeight * resolutionY));
            const context = canvas.getContext('2d');
            if (!context) return resolve(null);
            context.fillStyle = '#000';
            context.fillRect(0, 0, canvas.width, canvas.height);
            context.drawImage(
                imageElement,
                -win.windowX * resolutionX,
                -win.windowY * resolutionY,
                imageElement.naturalWidth,
                imageElement.naturalHeight
            );
            canvas.toBlob((blob) => {
                if (!blob || token.cancelled) return resolve(null);
                resolve(URL.createObjectURL(blob));
            }, 'image/png');
        };
        imageElement.onerror = () => resolve(null);
        imageElement.src = win.sourceUrl;
    });
}
