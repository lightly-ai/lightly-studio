import { describe, expect, it } from 'vitest';
import {
    createSlicMaskForLabels,
    extractCellMask,
    getLabelAtPoint,
    getSlicComputeOptions,
    resolveSlicImageUrl,
    upsampleCellMask,
    type SlicResult
} from './slic';

// The SLIC algorithm itself (clustering, boundaries, hierarchical merging)
// lives in @lightly-ai/slic and is tested there. These tests cover the
// app-side adapter: URL resolution and the SlicResult scale mapping.

const makeResult = (overrides: Partial<SlicResult> = {}): SlicResult => ({
    labels: new Int32Array([0, 1, 2, 3]),
    width: 2,
    height: 2,
    boundaries: new Uint8Array(4),
    pixelIndexes: new Uint32Array([0, 1, 2, 3]),
    segmentOffsets: new Uint32Array([0, 1, 2, 3, 4]),
    labelPixelIndexes: [[0], [1], [2], [3]],
    originalWidth: 4,
    originalHeight: 4,
    scaleX: 2,
    scaleY: 2,
    level: 'medium',
    ...overrides
});

describe('slic utilities', () => {
    it.each([
        ['coarse', { targetSegments: 80, compactness: 35, smoothing: 'bilateral' }],
        ['medium', { targetSegments: 240, compactness: 28, smoothing: 'bilateral' }],
        ['fine', { targetSegments: 480, compactness: 22, smoothing: 'bilateral' }]
    ] as const)('uses direct smoothed SLIC options for %s', (level, expected) => {
        expect(getSlicComputeOptions(level)).toEqual(expected);
    });

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

    it('extracts a single cell mask', () => {
        const mask = extractCellMask(new Int32Array([1, 1, 2, 1, 2, 2]), 3, 2, 2);

        expect(Array.from(mask)).toEqual([0, 0, 1, 0, 1, 1]);
    });

    it('maps original coordinates to the downscaled label grid', () => {
        const result = makeResult();

        expect(getLabelAtPoint(result, 0, 0)).toBe(0);
        expect(getLabelAtPoint(result, 3, 0)).toBe(1);
        expect(getLabelAtPoint(result, 0, 3)).toBe(2);
        expect(getLabelAtPoint(result, 3, 3)).toBe(3);
    });

    it('upsamples a selected cell back to the original image resolution', () => {
        const mask = upsampleCellMask(makeResult(), 1);

        expect(Array.from(mask)).toEqual([0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0]);
    });

    it('creates a low-resolution preview mask from touched labels', () => {
        const result = makeResult({
            labels: new Int32Array([0, 1, 2, 1]),
            pixelIndexes: new Uint32Array([0, 1, 3, 2]),
            segmentOffsets: new Uint32Array([0, 1, 3, 4]),
            labelPixelIndexes: [[0], [1, 3], [2]],
            originalWidth: 2,
            originalHeight: 2,
            scaleX: 1,
            scaleY: 1
        });

        expect(Array.from(createSlicMaskForLabels(result, [1, 2]))).toEqual([0, 1, 1, 1]);
    });
});
