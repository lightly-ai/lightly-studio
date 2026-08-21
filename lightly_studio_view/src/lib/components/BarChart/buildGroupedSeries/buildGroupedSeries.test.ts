import { describe, expect, it } from 'vitest';
import { buildGroupedSeries, categoryKey } from './buildGroupedSeries';
import type { CategoryCount, CategoryCountSeries } from '../types';

const identity = (count: number) => count;
const asPercent = (count: number, denominator: number) => count / denominator;

const categories: CategoryCount[] = [
    { label: 'car', count: 10 },
    { label: 'dog', count: 5 },
    { label: 'cat', count: 3 }
];

const series: CategoryCountSeries[] = [
    {
        id: 'tag-a',
        label: 'Reviewed',
        data: [
            { label: 'car', count: 6 },
            { label: 'dog', count: 2 }
        ]
    },
    {
        id: 'tag-b',
        label: 'Priority',
        data: [
            { label: 'car', count: 4 },
            { label: 'cat', count: 3 }
        ]
    }
];

const colors = new Map([
    ['tag-a', '#ff0000'],
    ['tag-b', '#0000ff']
]);

describe('categoryKey', () => {
    it('returns id when present', () => {
        expect(categoryKey({ id: 'my-id', label: 'My Label', count: 1 })).toBe('my-id');
    });

    it('falls back to label when id is absent', () => {
        expect(categoryKey({ label: 'My Label', count: 1 })).toBe('My Label');
    });
});

describe('buildGroupedSeries', () => {
    it('produces one ECharts series per input series', () => {
        const result = buildGroupedSeries(categories, series, colors, identity);
        expect(result).toHaveLength(2);
    });

    it('sets id and name from the input series', () => {
        const [a, b] = buildGroupedSeries(categories, series, colors, identity);
        expect(a.id).toBe('tag-a');
        expect(a.name).toBe('Reviewed');
        expect(b.id).toBe('tag-b');
        expect(b.name).toBe('Priority');
    });

    it('aligns data to the category order from the data array', () => {
        const [a, b] = buildGroupedSeries(categories, series, colors, identity);
        // categories: car=0, dog=1, cat=2
        expect(a.data).toEqual([6, 2, 0]); // cat missing → 0
        expect(b.data).toEqual([4, 0, 3]); // dog missing → 0
    });

    it('applies toChartValue to each count', () => {
        const seriesWithTotal: CategoryCountSeries[] = [
            { id: 'tag-a', label: 'Reviewed', data: [{ label: 'car', count: 5 }], totalCount: 10 }
        ];
        const [a] = buildGroupedSeries(
            [{ label: 'car', count: 10 }],
            seriesWithTotal,
            colors,
            asPercent
        );
        expect(a.data).toEqual([0.5]);
    });

    it('uses totalCount as denominator when provided', () => {
        const denominators: number[] = [];
        const captureDenominator = (count: number, denominator: number) => {
            denominators.push(denominator);
            return count;
        };
        const seriesWithTotal: CategoryCountSeries[] = [
            {
                id: 'tag-a',
                label: 'Reviewed',
                data: [{ label: 'car', count: 3 }],
                totalCount: 99
            }
        ];
        buildGroupedSeries(
            [{ label: 'car', count: 10 }],
            seriesWithTotal,
            colors,
            captureDenominator
        );
        expect(denominators[0]).toBe(99);
    });

    it('sums data counts as denominator when totalCount is absent', () => {
        const denominators: number[] = [];
        const captureDenominator = (count: number, denominator: number) => {
            denominators.push(denominator);
            return count;
        };
        const seriesNoTotal: CategoryCountSeries[] = [
            {
                id: 'tag-a',
                label: 'Reviewed',
                data: [
                    { label: 'car', count: 4 },
                    { label: 'dog', count: 6 }
                ]
            }
        ];
        buildGroupedSeries(
            [
                { label: 'car', count: 10 },
                { label: 'dog', count: 5 }
            ],
            seriesNoTotal,
            colors,
            captureDenominator
        );
        expect(denominators[0]).toBe(10); // 4 + 6
    });

    it('assigns the correct color from groupedColors', () => {
        const [a, b] = buildGroupedSeries(categories, series, colors, identity);
        expect(a.itemStyle.color).toBe('#ff0000');
        expect(b.itemStyle.color).toBe('#0000ff');
    });

    it('uses id-based key over label when id is present', () => {
        const categoriesWithId: CategoryCount[] = [{ id: 'c-1', label: 'car', count: 10 }];
        const seriesWithId: CategoryCountSeries[] = [
            {
                id: 'tag-a',
                label: 'Reviewed',
                data: [{ id: 'c-1', label: 'car', count: 7 }]
            }
        ];
        const [a] = buildGroupedSeries(categoriesWithId, seriesWithId, colors, identity);
        expect(a.data).toEqual([7]);
    });

    it('returns an empty array when groupedSeries is empty', () => {
        expect(buildGroupedSeries(categories, [], colors, identity)).toEqual([]);
    });
});
