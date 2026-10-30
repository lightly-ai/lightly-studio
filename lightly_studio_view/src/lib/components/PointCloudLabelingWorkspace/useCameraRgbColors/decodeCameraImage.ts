/** Cache decoded ImageData by Blob identity to avoid re-decoding on each render. */
const imageDataCache = new WeakMap<Blob, ImageData>();

/**
 * Decodes a JPEG blob to RGBA pixels off the DOM, caching by blob identity. Blobs are stable
 * per tick (shared from the tick-data query), so repeat requests reuse the decoded data.
 */
export async function decodeCameraImage(blob: Blob): Promise<ImageData> {
    const cached = imageDataCache.get(blob);
    if (cached) return cached;

    const bitmap = await createImageBitmap(blob);
    const canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Failed to get OffscreenCanvas 2D context');
    ctx.drawImage(bitmap, 0, 0);
    bitmap.close();
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    imageDataCache.set(blob, imageData);
    return imageData;
}
