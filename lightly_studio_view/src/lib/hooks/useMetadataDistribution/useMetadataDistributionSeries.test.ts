import { describe, expect, it } from 'vitest';
import { distributionToCategoryCounts, meanCategoryIndex } from './useMetadataDistributionSeries';

describe('distributionToCategoryCounts', () => {
    it('maps categorical value/count pairs straight through', () => {
        const data = distributionToCategoryCounts({
            key: 'weather',
            type: 'string',
            kind: 'categorical',
            categorical: [
                { value: 'sunny', count: 12 },
                { value: '(none)', count: 3 }
            ]
        });

        expect(data).toEqual([
            { label: 'sunny', count: 12 },
            { label: '(none)', count: 3 }
        ]);
    });

    it('turns numeric bins into range labels and appends (none) when missing values exist', () => {
        const data = distributionToCategoryCounts({
            key: 'speed',
            type: 'float',
            kind: 'numeric',
            bin_edges: [0, 2.5, 5],
            counts: [4, 6],
            none_count: 2
        });

        expect(data).toEqual([
            { label: '0–2.5', count: 4 },
            { label: '2.5–5', count: 6 },
            { label: '(none)', count: 2 }
        ]);
    });

    it('omits the (none) bucket when no values are missing', () => {
        const data = distributionToCategoryCounts({
            key: 'speed',
            type: 'integer',
            kind: 'numeric',
            bin_edges: [0, 10, 20],
            counts: [3, 7],
            none_count: 0
        });

        expect(data).toEqual([
            { label: '0–10', count: 3 },
            { label: '10–20', count: 7 }
        ]);
    });
});

describe('meanCategoryIndex', () => {
    // Two bins over [0, 10]: [0,5] centered at index 0, [5,10] centered at index 1.
    const edges = [0, 5, 10];

    it('maps a bin center to its integer index', () => {
        expect(meanCategoryIndex(edges, 2.5)).toBe(0);
        expect(meanCategoryIndex(edges, 7.5)).toBe(1);
    });

    it('maps a bin boundary to the half-index between bands', () => {
        // The mean at the shared 5.0 boundary sits at the right edge of bin 0.
        expect(meanCategoryIndex(edges, 5)).toBe(0.5);
    });

    it('interpolates within a bin proportionally', () => {
        // 1.25 is a quarter into bin 0: index 0 + (0.25 - 0.5) = -0.25.
        expect(meanCategoryIndex(edges, 1.25)).toBeCloseTo(-0.25, 5);
    });

    it('clamps values outside the histogram range to its edges', () => {
        expect(meanCategoryIndex(edges, -100)).toBe(-0.5);
        expect(meanCategoryIndex(edges, 100)).toBe(1.5);
    });

    it('returns undefined without at least two edges', () => {
        expect(meanCategoryIndex([], 1)).toBeUndefined();
        expect(meanCategoryIndex([3], 3)).toBeUndefined();
    });
});
