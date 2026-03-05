import parseColor from './parseColor';

const TRANSPARENT_DATA_URL =
    'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';
const maskDataUrlCache = new WeakMap<number[], Map<string, { dataUrl: string; height: number }>>();

export default function calculateBinaryMaskFromRLE(
    segmentation: number[],
    width: number,
    colorFill: string
): { dataUrl: string; height: number } {
    // Compute total number of pixels.
    const totalPixels = segmentation.reduce((acc, count) => acc + count, 0);
    // Calculate height; using Math.ceil to handle non-integer results.
    const height = Math.ceil(totalPixels / width);

    if (width <= 0 || height <= 0 || !Number.isFinite(width) || !Number.isFinite(height)) {
        // Return a minimal transparent data URL or throw an error, depending on requirements
        return {
            dataUrl: TRANSPARENT_DATA_URL,
            height: 0
        };
    }

    const cacheKey = `${width}:${colorFill}`;
    const cachedMaskDataUrl = maskDataUrlCache.get(segmentation)?.get(cacheKey);
    if (cachedMaskDataUrl) {
        return cachedMaskDataUrl;
    }

    // --- Environment Check (Optional but helpful for debugging tests) ---
    if (typeof document === 'undefined') {
        // This function fundamentally relies on the Canvas API.
        // If document doesn't exist, we're likely in a Node test env without mocks.
        throw new Error(
            'Canvas API (document) not available. Ensure tests mock the DOM and Canvas.'
        );
    }

    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    // Note: 'willReadFrequently' might not be supported/relevant in all mocks
    const ctx = canvas.getContext('2d', { willReadFrequently: true });

    if (!ctx) {
        // Check if context acquisition failed (less likely if document exists, but good practice)
        throw new Error('Failed to get canvas 2D context. Check canvas support or mocks.');
    }

    // --- Check for necessary methods ---
    // Add this check to fail fast in tests if the mock is incomplete
    if (typeof ctx.createImageData !== 'function' || typeof ctx.putImageData !== 'function') {
        throw new Error(
            `Canvas context mock is incomplete. Missing 'createImageData' or 'putImageData'. Please update test environment mocks (e.g., jest-canvas-mock).`
        );
    }
    // --- End Checks ---

    // Create an ImageData object. It's initialized to transparent black (all zeros).
    let imageData: ImageData;
    try {
        imageData = ctx.createImageData(width, height);
    } catch (e) {
        console.error(
            `Error calling ctx.createImageData(${width}, ${height}). Check mock implementation.`,
            e
        );
        throw e; // Re-throw after logging
    }

    const data = imageData.data; // Uint8ClampedArray: [R, G, B, A, R, G, B, A, ...]
    const bufferLength = data.length; // Cache length

    // Parse the fill color *once*
    const { r, g, b, a } = parseColor(colorFill);

    let currentPixelIndex = 0; // Tracks the logical pixel number (0 to width*height - 1)

    segmentation.forEach((count, index) => {
        if (count === 0) return; // Skip zero counts

        const isFillSegment = index % 2 !== 0;

        if (isFillSegment) {
            // Fill 'count' pixels
            const endPixelIndex = currentPixelIndex + count;
            let dataIndex = currentPixelIndex * 4;
            while (currentPixelIndex < endPixelIndex) {
                // Boundary check before writing
                if (dataIndex >= 0 && dataIndex < bufferLength - 3) {
                    data[dataIndex] = r;
                    data[dataIndex + 1] = g;
                    data[dataIndex + 2] = b;
                    data[dataIndex + 3] = a;
                }
                currentPixelIndex++;
                dataIndex += 4;
            }
        } else {
            // Skip 'count' pixels (ImageData is already transparent black)
            currentPixelIndex += count;
        }
    });

    // Put the manipulated pixel data onto the canvas in one go
    ctx.putImageData(imageData, 0, 0);

    // Generate the data URL (still potentially costly, but drawing is faster)
    let dataUrl = '';
    try {
        dataUrl = canvas.toDataURL(); // Defaults to 'image/png'
    } catch (e) {
        console.error('Error calling canvas.toDataURL(). Check mock implementation.', e);
        // Return minimal data URL or re-throw depending on desired test behavior on mock failure
        dataUrl = TRANSPARENT_DATA_URL;
        // throw e; // Alternatively, make the test fail hard
    }

    const result = { dataUrl, height };
    const cache = maskDataUrlCache.get(segmentation) ?? new Map<string, { dataUrl: string; height: number }>();
    cache.set(cacheKey, result);
    maskDataUrlCache.set(segmentation, cache);

    return result;
}
