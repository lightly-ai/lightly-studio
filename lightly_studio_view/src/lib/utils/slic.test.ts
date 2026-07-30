import { describe, expect, it } from 'vitest';
import { getSlicComputeOptions, resolveSlicImageUrl } from './slic';

// The SLIC algorithm itself (clustering, boundaries, hierarchical merging)
// lives in @lightly-ai/slic and is tested there. These tests cover the
// app-side adapter: URL resolution and product-level computation settings.

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
});
