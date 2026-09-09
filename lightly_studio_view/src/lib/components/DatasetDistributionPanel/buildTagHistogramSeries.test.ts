import { describe, expect, it } from 'vitest';
import { buildTagHistogramSeries, type HistogramComparison } from './buildTagHistogramSeries';

const width = { binEdges: [0, 1, 2], counts: [3, 4] };
const height = { binEdges: [0, 1, 2], counts: [1, 1] };

describe('buildTagHistogramSeries', () => {
    const comparisons: HistogramComparison[] = [
        { id: 'tag-a', label: 'Reviewed', histograms: { width, height } },
        { id: 'tag-b', label: 'Priority', histograms: { height } }
    ];

    it('names each tag that reported the key', () => {
        expect(buildTagHistogramSeries(comparisons, 'height')).toEqual([
            { id: 'tag-a', label: 'Reviewed', data: height },
            { id: 'tag-b', label: 'Priority', data: height }
        ]);
    });

    it('drops a tag that has no histogram for the key rather than zero-filling it', () => {
        expect(buildTagHistogramSeries(comparisons, 'width')).toEqual([
            { id: 'tag-a', label: 'Reviewed', data: width }
        ]);
    });

    it('returns nothing when no tag reported the key', () => {
        expect(buildTagHistogramSeries(comparisons, 'depth')).toEqual([]);
    });
});
