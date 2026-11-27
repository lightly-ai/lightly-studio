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

    it('splits whole-window camera-rgb colors back into per-segment slices', () => {
        const batch = createSegmentedPointBatch(segments);
        // Float32-exact values so slicing is compared without rounding error.
        const cameraColors = new Float32Array([1, 0, 0, 0.5, 0.5, 0.5, 0.25, 0.25, 0.25]);
        const actual = getPointCloudFrameColors(batch, 'camera-rgb', undefined, cameraColors);
        expect(Array.from(actual[0])).toEqual([1, 0, 0, 0.5, 0.5, 0.5]);
        expect(Array.from(actual[1])).toEqual([0.25, 0.25, 0.25]);
    });

    it('falls back to neutral per segment when camera-rgb colors are not ready', () => {
        const batch = createSegmentedPointBatch(segments);
        const actual = getPointCloudFrameColors(batch, 'camera-rgb');
        expect(actual.flatMap((colors) => Array.from(colors))).toEqual(Array(9).fill(0.5));
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

    it('highlights the points inside a cuboid and keeps the points outside on request', () => {
        const batch = {
            positions: new Float32Array([0, 0, 0, 5, 0, 0]),
            intensities: new Float32Array(2),
            colors: new Float32Array([1, 0, 0, 0, 0, 1]),
            count: 2
        };
        const cuboid = {
            center: [0, 0, 0],
            size: [1, 1, Infinity],
            rotation: [0, 0, 0, 1]
        } as const;

        const [dimmed] = getPointCloudFrameColors(batch, 'rgb', undefined, undefined, cuboid);
        // The inside point turns yellow; the outside point is dimmed.
        expect(Array.from(dimmed.slice(0, 3))).toEqual([
            1,
            expect.closeTo(0.663),
            expect.closeTo(0.068)
        ]);
        expect(dimmed[5]).toBeCloseTo(0.12);

        const [kept] = getPointCloudFrameColors(batch, 'rgb', undefined, undefined, {
            ...cuboid,
            keepOutside: true
        });
        expect(Array.from(kept.slice(0, 3))).toEqual(Array.from(dimmed.slice(0, 3)));
        expect(Array.from(kept.slice(3))).toEqual([0, 0, 1]);
    });
});

describe('range highlight', () => {
    const rangeSegments = [
        {
            positions: new Float32Array([0, 0, 0, 50, 0, 0]),
            intensities: new Float32Array([0, 0]),
            colors: new Float32Array([1, 1, 1, 1, 1, 1]),
            count: 2
        }
    ];

    it('dims points beyond the range radius', () => {
        const batch = createSegmentedPointBatch(rangeSegments);
        const [colors] = getPointCloudFrameColors(batch, 'rgb', undefined, undefined, undefined, {
            center: [0, 0],
            radius: 40
        });

        expect(Array.from(colors.subarray(0, 3))).toEqual([1, 1, 1]);
        for (const channel of colors.subarray(3, 6)) expect(channel).toBeLessThan(1);
    });

    it('keeps the full cuboid highlight beyond the range radius', () => {
        const batch = createSegmentedPointBatch(rangeSegments);
        const cuboid = {
            center: [50, 0, 0] as const,
            size: [2, 2, 2] as const,
            rotation: [0, 0, 0, 1] as const
        };
        const [withRange] = getPointCloudFrameColors(batch, 'rgb', undefined, undefined, cuboid, {
            center: [0, 0],
            radius: 40
        });

        // The highlight color has an 85 % weight; dimming it to 25 % would give at most 0.25.
        const highlightRed = 0.85;
        expect(withRange[3]).toBeGreaterThan(highlightRed);
    });

    it('keeps the colors without a range highlight', () => {
        const batch = createSegmentedPointBatch(rangeSegments);
        const [colors] = getPointCloudFrameColors(batch, 'rgb');

        expect(Array.from(colors)).toEqual([1, 1, 1, 1, 1, 1]);
    });
});
