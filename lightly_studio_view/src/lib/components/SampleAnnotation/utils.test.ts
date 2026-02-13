import { vi, beforeEach, afterEach } from 'vitest';
import {
    computeBoundingBoxFromMask,
    encodeBinaryMaskToRLE,
    decodeRLEToBinaryMask,
    maskToDataUrl,
    interpolateLineBetweenPoints
} from '$lib/components/SampleAnnotation/utils';

describe('SampleAnnotationUtils', () => {
    it('returns a 1x1 bounding box for a single active pixel', () => {
        const width = 4;
        const height = 3;

        // Pixel at (2, 1)
        const mask = new Uint8Array([0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]);

        const bbox = computeBoundingBoxFromMask(mask, width, height);

        expect(bbox).toEqual({
            x: 2,
            y: 1,
            width: 1,
            height: 1
        });
    });

    it('encodes an empty mask', () => {
        // Empty masks must return [0] to ensure a valid, decodable RLE
        const mask = new Uint8Array([]);

        const rle = encodeBinaryMaskToRLE(mask);

        expect(rle).toEqual([0]);
    });

    it('encodes a segmentation mask', () => {
        // Binary mask represented 1D array
        // Values: 0 = background, 1 = foreground
        const mask = new Uint8Array([0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1]);

        const rle = encodeBinaryMaskToRLE(mask);

        // Mask runs:
        //  3 zeros -> [0, 0, 0]
        //  5 ones  -> [1, 1, 1, 1, 1]
        //  2 zeros -> [0, 0]
        //  1 one   -> [1]
        expect(rle).toEqual([3, 5, 2, 1]);
    });

    it('decodes a RLE mask', () => {
        // Total pixels = width * height = 3 * 2 = 6
        const mask = decodeRLEToBinaryMask([2, 3, 1], 3, 2);

        // [2, 3, 1] means:
        //  2 zeros -> [0, 0]
        //  3 ones  -> [1, 1, 1]
        //  1 zero  -> [0]
        expect(mask).toEqual(new Uint8Array([0, 0, 1, 1, 1, 0]));
    });

    it('interpolates points along a line', () => {
        const from = { x: 0, y: 0 };
        const to = { x: 3, y: 4 };

        const points = interpolateLineBetweenPoints(from, to);

        expect(points).toHaveLength(10);
        expect(points[0]).toEqual({ x: 0.3, y: 0.4 });
        expect(points[points.length - 1]).toEqual(to);
    });

    describe('maskToDataUrl', () => {
        let mockCtx: {
            createImageData: ReturnType<typeof vi.fn>;
            putImageData: ReturnType<typeof vi.fn>;
        };
        let mockCanvas: {
            width: number;
            height: number;
            getContext: ReturnType<typeof vi.fn>;
            toDataURL: ReturnType<typeof vi.fn>;
        };
        let capturedImageData: { data: Uint8ClampedArray } | null = null;

        beforeEach(() => {
            capturedImageData = null;
            mockCtx = {
                createImageData: vi.fn((width: number, height: number) => ({
                    width,
                    height,
                    data: new Uint8ClampedArray(width * height * 4)
                })),
                putImageData: vi.fn((imageData: { data: Uint8ClampedArray }) => {
                    capturedImageData = imageData;
                })
            };
            mockCanvas = {
                width: 0,
                height: 0,
                getContext: vi.fn(() => mockCtx),
                toDataURL: vi.fn().mockReturnValue('data:image/png;base64,mockDataUrl')
            };

            vi.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
                if (tagName === 'canvas') {
                    return mockCanvas as unknown as HTMLCanvasElement;
                }
                throw new Error(`Unexpected createElement call: ${tagName}`);
            });
        });

        afterEach(() => {
            vi.restoreAllMocks();
        });

        it('converts a mask to a data URL', () => {
            const mask = new Uint8Array([0, 1, 1, 0]);
            const color = { r: 255, g: 0, b: 0, a: 128 };

            const dataUrl = maskToDataUrl(mask, 2, 2, color);

            expect(dataUrl).toEqual('data:image/png;base64,mockDataUrl');
            expect(mockCanvas.width).toEqual(2);
            expect(mockCanvas.height).toEqual(2);
            expect(mockCtx.createImageData).toHaveBeenCalledWith(2, 2);
            expect(mockCtx.putImageData).toHaveBeenCalledTimes(1);
            expect(mockCanvas.toDataURL).toHaveBeenCalledTimes(1);
        });

        it('sets correct pixel colors in image data', () => {
            const mask = new Uint8Array([0, 1, 1, 0]);
            const color = { r: 255, g: 0, b: 0, a: 128 };

            maskToDataUrl(mask, 2, 2, color);

            expect(capturedImageData).not.toBeNull();
            if (!capturedImageData) return;

            const data = capturedImageData.data;
            // Pixel 0: mask=0, should be transparent (all zeros)
            expect(data.slice(0, 4)).toEqual(new Uint8ClampedArray([0, 0, 0, 0]));
            // Pixel 1: mask=1, should be red with alpha 128
            expect(data.slice(4, 8)).toEqual(new Uint8ClampedArray([255, 0, 0, 128]));
            // Pixel 2: mask=1, should be red with alpha 128
            expect(data.slice(8, 12)).toEqual(new Uint8ClampedArray([255, 0, 0, 128]));
            // Pixel 3: mask=0, should be transparent
            expect(data.slice(12, 16)).toEqual(new Uint8ClampedArray([0, 0, 0, 0]));
        });
    });
});
