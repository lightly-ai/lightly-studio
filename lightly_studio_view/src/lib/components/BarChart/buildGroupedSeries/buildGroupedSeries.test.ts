import { describe, expect, it } from 'vitest';
import { buildGroupedSeries, categoryKey } from './buildGroupedSeries';
import type { CategoryCount, CategoryCountSeries } from '../types';

const identity = (count: number) => count;

const colors = new Map([
    ['s1', '#aaa'],
    ['s2', '#bbb']
]);

const categories: CategoryCount[] = [
    { label: 'car', count: 10 },
    { label: 'dog', count: 5 }
];

const series: CategoryCountSeries[] = [
    {
        id: 's1',
        label: 'Tag A',
        data: [
            { label: 'car', count: 3 },
            { label: 'dog', count: 1 }
        ]
    },
    {
        id: 's2',
        label: 'Tag B',
        data: [{ label: 'car', count: 7 }]
    }
];

describe('categoryKey', () => {
    it('returns id when present', () => {
        expect(categoryKey({ id: 'my-id', label: 'My Label', count: 1 })).toBe('my-id');
    });

    it('falls back to label when id is absent', () => {
        expect(categoryKey({ label: 'My Label', count: 1 })).toBe('My Label');
    });
});

describe('buildGroupedSeries', () => {
    it('produces one ECharts series entry per grouped series', () => {
        const result = buildGroupedSeries(categories, series, colors, identity);
        expect(result).toHaveLength(2);
    });

    it('maps series id and label to the ECharts entry', () => {
        const result = buildGroupedSeries(categories, series, colors, identity);
        expect(result[0]).toMatchObject({ id: 's1', name: 'Tag A', type: 'bar' });
        expect(result[1]).toMatchObject({ id: 's2', name: 'Tag B', type: 'bar' });
    });

    it('aligns data values with the category axis order', () => {
        const result = buildGroupedSeries(categories, series, colors, identity);
        expect(result[0].data).toEqual([3, 1]);
        expect(result[1].data).toEqual([7, 0]); // dog missing in s2 → zero-fill
    });

    it('zero-fills categories absent from a series', () => {
        const result = buildGroupedSeries(categories, series, colors, identity);
        expect(result[1].data[1]).toBe(0);
    });

    it('applies the color from groupedColors', () => {
        const result = buildGroupedSeries(categories, series, colors, identity);
        expect(result[0].itemStyle.color).toBe('#aaa');
        expect(result[1].itemStyle.color).toBe('#bbb');
    });

    it('uses toChartValue to transform counts', () => {
        const double = (count: number) => count * 2;
        const result = buildGroupedSeries(categories, series, colors, double);
        expect(result[0].data).toEqual([6, 2]);
    });

    it('uses series.totalCount as the denominator when provided', () => {
        const seriesWithTotal: CategoryCountSeries[] = [
            { id: 's1', label: 'Tag A', data: [{ label: 'car', count: 3 }], totalCount: 100 }
        ];
        const toPercent = (count: number, total: number) => (count / total) * 100;
        const result = buildGroupedSeries(categories, seriesWithTotal, colors, toPercent);
        expect(result[0].data[0]).toBeCloseTo(3);
    });

    it('keys by id when categories share the same label', () => {
        const duplicateCategories: CategoryCount[] = [
            { id: 'id-1', label: 'Missing', count: 5 },
            { id: 'id-2', label: 'Missing', count: 8 }
        ];
        const seriesWithIds: CategoryCountSeries[] = [
            {
                id: 's1',
                label: 'Tag A',
                data: [
                    { id: 'id-1', label: 'Missing', count: 2 },
                    { id: 'id-2', label: 'Missing', count: 6 }
                ]
            }
        ];
        const result = buildGroupedSeries(duplicateCategories, seriesWithIds, colors, identity);
        expect(result[0].data).toEqual([2, 6]);
    });
});
