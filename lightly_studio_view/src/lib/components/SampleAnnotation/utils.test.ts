import {
    computeBoundingBoxFromMask,
    encodeBinaryMaskToRLE,
    decodeRLEToBinaryMask,
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
});
