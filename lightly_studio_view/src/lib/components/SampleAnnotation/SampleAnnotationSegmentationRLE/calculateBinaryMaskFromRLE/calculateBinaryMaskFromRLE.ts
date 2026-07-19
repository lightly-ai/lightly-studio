import parseColor from './parseColor';

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
            dataUrl:
                'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=',
            height: 0
        };
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
    let imageDataIndex = 0; // Tracks the index in the flat ImageData buffer (0 to bufferLength - 4)

    segmentation.forEach((count, index) => {
        if (count === 0) return; // Skip zero counts

        const isFillSegment = index % 2 !== 0;

        if (isFillSegment) {
            // Fill 'count' pixels
            const endPixelIndex = currentPixelIndex + count;
            while (currentPixelIndex < endPixelIndex) {
                // Calculate buffer index *only once* per pixel
                const y = Math.floor(currentPixelIndex / width);
                const x = currentPixelIndex % width;
                imageDataIndex = (y * width + x) * 4; // Calculate the byte index for this pixel

                // Boundary check before writing
                if (imageDataIndex >= 0 && imageDataIndex < bufferLength - 3) {
                    data[imageDataIndex] = r;
                    data[imageDataIndex + 1] = g;
                    data[imageDataIndex + 2] = b;
                    data[imageDataIndex + 3] = a;
                }
                currentPixelIndex++; // Move to the next logical pixel
            }
        } else {
            // Skip 'count' pixels (ImageData is already transparent black)
            currentPixelIndex += count;
            // No need to update imageDataIndex here, it will be recalculated
            // when the next fill segment starts.
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
        dataUrl =
            'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';
        // throw e; // Alternatively, make the test fail hard
    }

    return { dataUrl, height };
}
