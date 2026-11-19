import { describe, expect, it } from 'vitest';
import { getPlotRequestFilter } from './getPlotRequestFilter';

const region = {
    polygon: [
        { x: 0, y: 0 },
        { x: 1, y: 0 },
        { x: 1, y: 1 }
    ]
};

describe('getPlotRequestFilter', () => {
    it('returns null for null', () => {
        expect(getPlotRequestFilter(null)).toBeNull();
    });

    it('drops a sample_filter that only held the region and picks', () => {
        const filter = {
            filter_type: 'image',
            sample_filter: { sample_ids: ['a'], embedding_region: region }
        };
        expect(getPlotRequestFilter(filter)).toEqual({ filter_type: 'image' });
    });

    it('keeps the other sample_filter keys', () => {
        const filter = {
            filter_type: 'image',
            sample_filter: { tag_ids: ['t'], sample_ids: [] as string[] }
        };
        expect(getPlotRequestFilter(filter)).toEqual({
            filter_type: 'image',
            sample_filter: { tag_ids: ['t'] }
        });
    });

    it('gives the same request before and after a selection', () => {
        const before = { filter_type: 'image', sample_filter: { tag_ids: ['t'] } };
        const after = {
            filter_type: 'image',
            sample_filter: { tag_ids: ['t'], embedding_region: region, sample_ids: [] }
        };
        expect(getPlotRequestFilter(after)).toEqual(getPlotRequestFilter(before));
    });

    it('treats undefined, null, [] and {} as empty', () => {
        const filter = {
            filter_type: 'image',
            sample_filter: { tag_ids: [], a: undefined, b: null, c: {} }
        };
        expect(getPlotRequestFilter(filter)).toEqual({ filter_type: 'image' });
    });

    it('does not change the input', () => {
        const filter = { filter_type: 'image', sample_filter: { sample_ids: ['a'] } };
        getPlotRequestFilter(filter);
        expect(filter).toEqual({ filter_type: 'image', sample_filter: { sample_ids: ['a'] } });
    });
});
