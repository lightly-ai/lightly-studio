import { getImageURLById } from '$lib/utils';

interface Size {
    width: number;
    height: number;
}

// Decodes a sample image straight to the model's input size, so a huge image never needs a
// full-size canvas. Also returns the original size, to scale the boxes back.
export const loadImageBitmap = async (
    sampleId: string,
    size: Size
): Promise<{ bitmap: ImageBitmap; original: Size }> => {
    const response = await fetch(getImageURLById(sampleId));
    if (!response.ok) {
        throw new Error(`Could not load the image of sample ${sampleId}: HTTP ${response.status}.`);
    }
    const blob = await response.blob();
    const fullSize = await createImageBitmap(blob);
    const original = { width: fullSize.width, height: fullSize.height };
    fullSize.close();
    const bitmap = await createImageBitmap(blob, {
        resizeWidth: size.width,
        resizeHeight: size.height,
        resizeQuality: 'high'
    });
    return { bitmap, original };
};
