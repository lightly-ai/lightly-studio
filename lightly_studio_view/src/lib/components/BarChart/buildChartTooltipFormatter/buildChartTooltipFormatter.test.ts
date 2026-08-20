import { describe, expect, it } from 'vitest';
import { buildChartTooltipFormatter } from './buildChartTooltipFormatter';
import type { CategoryCount, CategoryCountSeries } from '../types';

const data: CategoryCount[] = [
    { label: 'car', count: 80 },
    { label: 'dog', count: 20 }
];

const totalCount = 100;

const fmt = (
    isGrouped: boolean,
    categories: CategoryCount[],
    grouped: CategoryCountSeries[],
    total: number,
    hasFilter: boolean
) => buildChartTooltipFormatter(isGrouped, categories, grouped, total, hasFilter);

describe('buildChartTooltipFormatter — standard mode', () => {
    it('returns empty string for empty params', () => {
        const formatter = fmt(false, data, [], totalCount, false);
        expect(formatter([])).toBe('');
    });

    it('shows count and percentage for a matched category', () => {
        const formatter = fmt(false, data, [], totalCount, false);
        expect(formatter([{ name: 'car', value: 80 }])).toBe(
            '<b>car</b><br/>Count: <b>80</b> (80.0%)'
        );
    });

    it('shows zero count for an unrecognised category name', () => {
        const formatter = fmt(false, data, [], totalCount, false);
        expect(formatter([{ name: 'unknown', value: 0 }])).toBe(
            '<b>unknown</b><br/>Count: <b>0</b> (0.0%)'
        );
    });

    it('omits the percentage when totalCount is 0', () => {
        const formatter = fmt(false, [{ label: 'car', count: 0 }], [], 0, false);
        expect(formatter([{ name: 'car', value: 0 }])).toBe('<b>car</b><br/>Count: <b>0</b>');
    });

    it('escapes HTML in category labels', () => {
        const xss: CategoryCount[] = [{ label: '<script>alert(1)</script>', count: 10 }];
        const formatter = fmt(false, xss, [], 10, false);
        expect(formatter([{ name: '<script>alert(1)</script>', value: 10 }])).toBe(
            '<b>&lt;script&gt;alert(1)&lt;/script&gt;</b><br/>Count: <b>10</b> (100.0%)'
        );
    });

    it('shows filtered and total counts when hasActiveFilter is true and filteredCount differs', () => {
        const filtered: CategoryCount[] = [{ label: 'car', count: 100, filteredCount: 60 }];
        const formatter = fmt(false, filtered, [], 100, true);
        expect(formatter([{ name: 'car', value: 60 }])).toBe(
            '<b>car</b><br/>Count: <b>60</b> (60.0%) of <b>100</b> (100.0%) total'
        );
    });

    it('omits filtered/total split when filteredCount equals count', () => {
        const noFilter: CategoryCount[] = [{ label: 'car', count: 100, filteredCount: 100 }];
        const formatter = fmt(false, noFilter, [], 100, true);
        expect(formatter([{ name: 'car', value: 100 }])).toBe(
            '<b>car</b><br/>Count: <b>100</b> (100.0%)'
        );
    });

    it('omits filtered/total split when hasActiveFilter is false even if filteredCount is set', () => {
        const withField: CategoryCount[] = [{ label: 'car', count: 100, filteredCount: 60 }];
        const formatter = fmt(false, withField, [], 100, false);
        expect(formatter([{ name: 'car', value: 60 }])).toBe(
            '<b>car</b><br/>Count: <b>100</b> (100.0%)'
        );
    });

    it('matches by id when the category has one', () => {
        const withId: CategoryCount[] = [{ id: 'my-id', label: 'car', count: 50 }];
        const formatter = fmt(false, withId, [], 100, false);
        expect(formatter([{ name: 'my-id', value: 50 }])).toBe(
            '<b>car</b><br/>Count: <b>50</b> (50.0%)'
        );
    });
});

describe('buildChartTooltipFormatter — grouped mode', () => {
    const groupedSeries: CategoryCountSeries[] = [
        {
            id: 'tag-a',
            label: 'Reviewed',
            data: [
                { label: 'car', count: 3 },
                { label: 'dog', count: 0 }
            ]
        },
        {
            id: 'tag-b',
            label: 'Priority',
            data: [{ label: 'car', count: 1 }]
        }
    ];

    it('returns empty string for empty params', () => {
        const formatter = fmt(true, data, groupedSeries, totalCount, false);
        expect(formatter([])).toBe('');
    });

    it('formats each series line with marker and count', () => {
        const formatter = fmt(true, data, groupedSeries, totalCount, false);
        expect(
            formatter([
                { name: 'car', value: 3, seriesName: 'Reviewed', marker: '● ', seriesIndex: 0 },
                { name: 'car', value: 1, seriesName: 'Priority', marker: '■ ', seriesIndex: 1 }
            ])
        ).toBe('<b>car</b><br/>● Reviewed: <b>3</b> (100.0%)<br/>■ Priority: <b>1</b> (100.0%)');
    });

    it('falls back to index when seriesIndex is absent', () => {
        const formatter = fmt(true, data, groupedSeries, totalCount, false);
        expect(
            formatter([
                { name: 'car', value: 3, seriesName: 'Reviewed', marker: '● ' },
                { name: 'car', value: 1, seriesName: 'Priority', marker: '■ ' }
            ])
        ).toBe('<b>car</b><br/>● Reviewed: <b>3</b> (100.0%)<br/>■ Priority: <b>1</b> (100.0%)');
    });

    it('shows 0 for a category not in the series data', () => {
        const formatter = fmt(true, data, groupedSeries, totalCount, false);
        expect(
            formatter([
                { name: 'dog', value: 0, seriesName: 'Priority', marker: '', seriesIndex: 1 }
            ])
        ).toBe('<b>dog</b><br/>Priority: <b>0</b> (0.0%)');
    });

    it('uses series.totalCount as the denominator when provided', () => {
        const seriesWithTotal: CategoryCountSeries[] = [
            {
                id: 'tag-a',
                label: 'Reviewed',
                data: [{ label: 'car', count: 3 }],
                totalCount: 10
            }
        ];
        const formatter = fmt(true, data, seriesWithTotal, totalCount, false);
        expect(
            formatter([{ name: 'car', value: 3, seriesName: 'Reviewed', marker: '', seriesIndex: 0 }])
        ).toBe('<b>car</b><br/>Reviewed: <b>3</b> (30.0%)');
    });

    it('escapes HTML in category name and series name', () => {
        const xssSeries: CategoryCountSeries[] = [
            { id: 'x', label: '<b>bold</b>', data: [{ label: '<script>', count: 5 }] }
        ];
        const formatter = fmt(true, data, xssSeries, totalCount, false);
        expect(
            formatter([{ name: '<script>', value: 5, seriesName: '<b>bold</b>', marker: '', seriesIndex: 0 }])
        ).toBe('<b>&lt;script&gt;</b><br/>&lt;b&gt;bold&lt;/b&gt;: <b>5</b> (100.0%)');
    });
});
