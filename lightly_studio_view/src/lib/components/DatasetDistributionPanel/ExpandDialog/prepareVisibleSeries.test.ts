import { describe, expect, it } from 'vitest';
import { prepareVisibleSeries } from './prepareVisibleSeries';

const series = [
    {
        id: 'a',
        label: 'A',
        data: [
            { label: 'cat', count: 10 },
            { label: 'dog', count: 20 },
            { label: 'bird', count: 30 }
        ]
    }
];

describe('prepareVisibleSeries', () => {
    it('filters data to visible labels', () => {
        const result = prepareVisibleSeries(series, new Set(['cat', 'dog']));
        expect(result[0].data).toHaveLength(2);
        expect(result[0].data.map((d) => d.label)).toEqual(['cat', 'dog']);
    });

    it('sets totalCount from full data before filtering', () => {
        const result = prepareVisibleSeries(series, new Set(['cat']));
        expect(result[0].totalCount).toBe(60);
        expect(result[0].data).toHaveLength(1);
    });

    it('preserves an explicit totalCount', () => {
        const withTotal = [{ ...series[0], totalCount: 999 }];
        const result = prepareVisibleSeries(withTotal, new Set(['cat']));
        expect(result[0].totalCount).toBe(999);
    });
});
