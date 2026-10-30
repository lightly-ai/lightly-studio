import { describe, expect, it } from 'vitest';
import { createSegmentedPointBatch } from '$lib/hooks/useCloudPointFrame/createSegmentedPointBatch';
import { getPointCloudColors } from './getPointCloudColors';
import { getPointCloudFrameColors } from './getPointCloudFrameColors';
import type { ColorMode } from './pointCloudUtils';

const segments = [
    {
        positions: new Float32Array([0, 0, 0, 0.1, 0, 0.1]),
        intensities: new Float32Array([0, 10]),
        colors: new Float32Array([1, 0, 0, 0, 1, 0]),
        count: 2
    },
    {
        positions: new Float32Array([1, 0, 1]),
        intensities: new Float32Array([20]),
        colors: new Float32Array([0, 0, 1]),
        count: 1
    }
];

describe('sensor frame colors', () => {
    it.each<ColorMode>([
        'none',
        'rgb',
        'intensity',
        'height',
        'distance',
        'density',
        'height-distance',
        'height-density'
    ])('preserves the combined window color mapping for %s', (mode) => {
        const batch = createSegmentedPointBatch(segments);
        const expected = getPointCloudColors(batch, mode);
        const actual = getPointCloudFrameColors(batch, mode);
        expect(new Float32Array(actual.flatMap((colors) => Array.from(colors)))).toEqual(expected);
    });

    it('uses the custom intensity range and preserves the mixed RGB fallback', () => {
        const batch = createSegmentedPointBatch(segments);
        expect(getPointCloudFrameColors(batch, 'intensity', [0, 40])[0]).toEqual(
            getPointCloudColors(batch, 'intensity', [0, 40]).subarray(0, 6)
        );
        const mixed = createSegmentedPointBatch([
            segments[0],
            { ...segments[1], colors: undefined }
        ]);
        expect(
            getPointCloudFrameColors(mixed, 'rgb').flatMap((colors) => Array.from(colors))
        ).toEqual(Array(9).fill(0.5));
    });
});
