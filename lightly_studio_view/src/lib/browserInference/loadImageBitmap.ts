import { getImageURLById } from '$lib/utils';

interface Size {
    width: number;
    height: number;
}

// Decodes a sample image once and resizes the bitmap to the model's input size, so a huge
// image never needs a full-size canvas. Also returns the original size, to scale the boxes back.
// The full-size decode still peaks at width * height * 4 bytes of memory.
export const loadImageBitmap = async (
    sampleId: string,
    size: Size
): Promise<{ bitmap: ImageBitmap; original: Size }> => {
    const response = await fetch(getImageURLById(sampleId));
    if (!response.ok) {
        throw new Error(`Could not load the image of sample ${sampleId}: HTTP ${response.status}.`);
    }
    const fullSize = await createImageBitmap(await response.blob());
    const original = { width: fullSize.width, height: fullSize.height };
    try {
        const bitmap = await createImageBitmap(fullSize, {
            resizeWidth: size.width,
            resizeHeight: size.height,
            resizeQuality: 'high'
        });
        return { bitmap, original };
    } finally {
        fullSize.close();
    }
};
