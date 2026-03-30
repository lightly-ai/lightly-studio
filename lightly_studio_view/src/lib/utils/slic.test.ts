import { describe, expect, it } from 'vitest';
import {
    buildLabelPixelIndexes,
    createSlicMaskForLabels,
    computeBoundaryMask,
    computeSuperpixels,
    deriveMergedLevel,
    extractCellMask,
    forEachOriginalPixelRangeForLabel,
    getLabelAtPoint,
    resolveSlicImageUrl,
    upsampleCellMask
} from './slic';

describe('slic utilities', () => {
    it('keeps the original image URL outside dev mode', () => {
        expect(
            resolveSlicImageUrl('http://localhost:8001/images/sample/sample-1', {
                isDev: false,
                samplesUrl: 'http://localhost:8001/images'
            })
        ).toBe('http://localhost:8001/images/sample/sample-1');
    });

    it('rewrites sample images to a same-origin dev path for canvas loading', () => {
        expect(
            resolveSlicImageUrl('http://localhost:8001/images/sample/sample-1?v=2', {
                isDev: true,
                samplesUrl: 'http://localhost:8001/images'
            })
        ).toBe('/images/sample/sample-1?v=2');
    });

    it('computes superpixel labels with the expected shape', () => {
        const imageData = {
            width: 4,
            height: 4,
            data: new Uint8ClampedArray([
                255, 0, 0, 255, 255, 0, 0, 255, 0, 255, 0, 255, 0, 255, 0, 255,
                255, 0, 0, 255, 255, 0, 0, 255, 0, 255, 0, 255, 0, 255, 0, 255,
                0, 0, 255, 255, 0, 0, 255, 255, 255, 255, 0, 255, 255, 255, 0, 255,
                0, 0, 255, 255, 0, 0, 255, 255, 255, 255, 0, 255, 255, 255, 0, 255
            ])
        };

        const result = computeSuperpixels(imageData, { level: 'medium', maxIterations: 2 });

        expect(result.labels).toHaveLength(16);
        expect(result.boundaries).toHaveLength(16);
        expect(result.labelPixelIndexes.length).toBeGreaterThan(0);
        expect(Math.max(...result.labels)).toBeGreaterThanOrEqual(0);
    });

    it('builds label pixel indexes for cheap label lookups', () => {
        expect(
            buildLabelPixelIndexes(
                new Int32Array([
                    0, 1, 0,
                    2, 1, 2
                ])
            )
        ).toEqual([[0, 2], [1, 4], [3, 5]]);
    });

    it('extracts a boundary mask from neighboring label changes', () => {
        const labels = new Int32Array([
            0, 0, 1,
            0, 1, 1,
            2, 2, 1
        ]);

        const boundaries = computeBoundaryMask(labels, 3, 3);

        expect(Array.from(boundaries)).toEqual([
            0, 1, 1,
            1, 1, 0,
            1, 1, 1
        ]);
    });

    it('extracts a single cell mask', () => {
        const mask = extractCellMask(
            new Int32Array([
                1, 1, 2,
                1, 2, 2
            ]),
            3,
            2,
            2
        );

        expect(Array.from(mask)).toEqual([0, 0, 1, 0, 1, 1]);
    });

    it('maps original coordinates to the downscaled label grid', () => {
        const result = {
            labels: new Int32Array([
                0, 1,
                2, 3
            ]),
            width: 2,
            height: 2,
            boundaries: new Uint8Array(4),
            labelPixelIndexes: [[0], [1], [2], [3]],
            originalWidth: 4,
            originalHeight: 4,
            scaleX: 2,
            scaleY: 2,
            level: 'medium' as const
        };

        expect(getLabelAtPoint(result, 0, 0)).toBe(0);
        expect(getLabelAtPoint(result, 3, 0)).toBe(1);
        expect(getLabelAtPoint(result, 0, 3)).toBe(2);
        expect(getLabelAtPoint(result, 3, 3)).toBe(3);
    });

    it('upsamples a selected cell back to the original image resolution', () => {
        const result = {
            labels: new Int32Array([
                0, 1,
                2, 3
            ]),
            width: 2,
            height: 2,
            boundaries: new Uint8Array(4),
            labelPixelIndexes: [[0], [1], [2], [3]],
            originalWidth: 4,
            originalHeight: 4,
            scaleX: 2,
            scaleY: 2,
            level: 'medium' as const
        };

        const mask = upsampleCellMask(result, 1);

        expect(Array.from(mask)).toEqual([
            0, 0, 1, 1,
            0, 0, 1, 1,
            0, 0, 0, 0,
            0, 0, 0, 0
        ]);
    });

    it('creates a low-resolution preview mask from touched labels', () => {
        const result = {
            labels: new Int32Array([0, 1, 2, 1]),
            width: 2,
            height: 2,
            boundaries: new Uint8Array(4),
            labelPixelIndexes: [[0], [1, 3], [2]],
            originalWidth: 2,
            originalHeight: 2,
            scaleX: 1,
            scaleY: 1,
            level: 'medium' as const
        };

        expect(Array.from(createSlicMaskForLabels(result, [1, 2]))).toEqual([0, 1, 1, 1]);
    });

    it('maps one label to original-image paint ranges without allocating a full-size cell mask', () => {
        const result = {
            labels: new Int32Array([
                0, 1,
                2, 3
            ]),
            width: 2,
            height: 2,
            boundaries: new Uint8Array(4),
            labelPixelIndexes: [[0], [1], [2], [3]],
            originalWidth: 4,
            originalHeight: 4,
            scaleX: 2,
            scaleY: 2,
            level: 'medium' as const
        };

        const ranges: Array<[number, number, number, number]> = [];
        forEachOriginalPixelRangeForLabel(result, 1, (startX, endX, startY, endY) => {
            ranges.push([startX, endX, startY, endY]);
        });

        expect(ranges).toEqual([[2, 4, 0, 2]]);
    });

    it('derives coarser labels by merging fine labels instead of recomputing them', () => {
        const fineLabels = new Int32Array([
            0, 0, 1, 1, 2, 2, 3, 3,
            0, 0, 1, 1, 2, 2, 3, 3,
            4, 4, 5, 5, 6, 6, 7, 7,
            4, 4, 5, 5, 6, 6, 7, 7,
            8, 8, 9, 9, 10, 10, 11, 11,
            8, 8, 9, 9, 10, 10, 11, 11,
            12, 12, 13, 13, 14, 14, 15, 15,
            12, 12, 13, 13, 14, 14, 15, 15
        ]);

        const merged = deriveMergedLevel({
            sourceLabels: fineLabels,
            width: 8,
            height: 8,
            targetSegments: 4
        });

        expect(Array.from(merged)).toEqual([
            0, 0, 0, 0, 1, 1, 1, 1,
            0, 0, 0, 0, 1, 1, 1, 1,
            0, 0, 0, 0, 1, 1, 1, 1,
            0, 0, 0, 0, 1, 1, 1, 1,
            2, 2, 2, 2, 3, 3, 3, 3,
            2, 2, 2, 2, 3, 3, 3, 3,
            2, 2, 2, 2, 3, 3, 3, 3,
            2, 2, 2, 2, 3, 3, 3, 3
        ]);
    });
});
