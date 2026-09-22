import { describe, expect, it } from 'vitest';
import { selectCategoricalCounts, selectCategoricalSeries } from './selectCategoricalCounts';
import type { DistributionConfig } from './types';

const config: DistributionConfig = {
    mode: 'topN',
    n: 2,
    sortBy: 'count',
    manualClasses: [],
    orientation: 'horizontal'
};
const data = [
    { id: 'a', label: 'Alpha', count: 10, filteredCount: 4 },
    { id: 'b', label: 'Beta', count: 6, filteredCount: 2 },
    { id: 'c', label: 'Gamma', count: 3, filteredCount: 1 },
    { id: 'd', label: 'Delta', count: 1, filteredCount: 0 }
];

describe('selectCategoricalCounts', () => {
    it('aggregates hidden counts and filtered counts without making Other selectable', () => {
        const visible = selectCategoricalCounts(data, config);
        expect(visible).toEqual([
            data[0],
            data[1],
            {
                id: '["other"]',
                label: 'Other',
                count: 4,
                filteredCount: 1,
                selectable: false,
                pinned: true
            }
        ]);
        expect(visible.reduce((sum, item) => sum + item.count, 0)).toBe(20);
    });

    it('sorts the complete list by name before selecting the visible values', () => {
        expect(
            selectCategoricalCounts(data, { ...config, n: 3, sortBy: 'name' }).map(
                (item) => item.label
            )
        ).toEqual(['Alpha', 'Beta', 'Delta', 'Other']);
    });

    it('shows every value without Other when the limit reaches the category count', () => {
        expect(selectCategoricalCounts(data, { ...config, n: 30 })).toEqual(data);
        expect(selectCategoricalCounts([], config)).toEqual([]);
    });

    it('keeps only explicitly selected values in manual mode', () => {
        expect(
            selectCategoricalCounts(data, { ...config, mode: 'manual', manualClasses: ['d'] })
        ).toEqual([data[3]]);
    });

    it('keeps Missing visible and distinguishes a literal Other value', () => {
        const missing = { id: 'missing', label: 'Missing', count: 1, pinned: true };
        const visible = selectCategoricalCounts(
            [{ id: 'literal', label: 'Other', count: 30 }, ...data, missing],
            config
        );
        expect(visible.map((item) => item.label)).toEqual([
            'Other',
            'Missing',
            'Other (aggregated)'
        ]);
        expect(visible.at(-1)?.count).toBe(20);
    });

    it('includes a backend Other bucket when using an older backend', () => {
        const visible = selectCategoricalCounts(
            [...data, { id: '["other"]', label: 'Other', count: 5, pinned: true }],
            config
        );
        expect(visible.map((item) => item.label)).toEqual(['Alpha', 'Other']);
        expect(visible.at(-1)?.count).toBe(15);
    });
});

describe('selectCategoricalSeries', () => {
    const series = [
        {
            id: 'tag',
            label: 'Reviewed',
            data: [
                { id: 'a', label: 'Alpha', count: 1 },
                { id: 'c', label: 'Gamma', count: 7 },
                { id: 'd', label: 'Delta', count: 2 }
            ]
        }
    ];

    it('uses the shared axis rather than picking different top values for each tag', () => {
        const visible = selectCategoricalCounts(data, config);
        const result = selectCategoricalSeries(series, visible, true);
        expect(result[0].totalCount).toBe(10);
        expect(result[0].data).toEqual([
            series[0].data[0],
            expect.objectContaining({ id: '["other"]', count: 9, selectable: false })
        ]);
    });

    it('preserves the percentage denominator for manual selections', () => {
        const result = selectCategoricalSeries(series, [data[3]], false);
        expect(result[0].totalCount).toBe(10);
        expect(result[0].data).toEqual([series[0].data[2]]);
    });
});
