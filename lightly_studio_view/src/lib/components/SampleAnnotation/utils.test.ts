import {
    computeBoundingBoxFromMask,
    encodeBinaryMaskToRLE,
    decodeRLEToBinaryMask
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
        const mask = new Uint8Array([]);

        const rle = encodeBinaryMaskToRLE(mask);

        expect(rle).toEqual([0]);
    });

    it('encodes a segmentation mask', () => {
        const mask = new Uint8Array([0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1]);

        const rle = encodeBinaryMaskToRLE(mask);

        expect(rle).toEqual([3, 5, 2, 1]);
    });

    it('encodes an empty mask', () => {
        const mask = new Uint8Array([]);

        const rle = encodeBinaryMaskToRLE(mask);

        expect(rle).toEqual([0]);
    });

    it('decodes a RLE mask', () => {
        const mask = decodeRLEToBinaryMask([2, 3, 1], 3, 2);

        expect(mask).toEqual(new Uint8Array([0, 0, 1, 1, 1, 0]));
    });
});
