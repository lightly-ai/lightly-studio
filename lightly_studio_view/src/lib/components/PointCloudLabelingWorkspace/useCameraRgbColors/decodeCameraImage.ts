/** Decodes an encoded camera image inside the projection worker. */
export async function decodeCameraImage(blob: Blob): Promise<ImageData> {
    const bitmap = await createImageBitmap(blob);
    try {
        const canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
        const ctx = canvas.getContext('2d');
        if (!ctx) throw new Error('Failed to get OffscreenCanvas 2D context');
        ctx.drawImage(bitmap, 0, 0);
        return ctx.getImageData(0, 0, canvas.width, canvas.height);
    } finally {
        bitmap.close();
    }
}
