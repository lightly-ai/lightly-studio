import { describe, expect, it } from 'vitest';
import { buildChartTooltipFormatter } from './buildChartTooltipFormatter';
import type { CategoryCount, CategoryCountSeries } from '../types';

const data: CategoryCount[] = [
    { label: 'car', count: 6 },
    { label: 'dog', count: 4 }
];

const groupedSeries: CategoryCountSeries[] = [
    {
        id: 'tag-a',
        label: 'Reviewed',
        data: [
            { label: 'car', count: 3 },
            { label: 'dog', count: 2 }
        ]
    },
    {
        id: 'tag-b',
        label: 'Priority',
        data: [{ label: 'car', count: 1 }],
        totalCount: 10
    }
];

const param = (name: string, value: number, overrides: object = {}) => ({
    name,
    value,
    ...overrides
});

describe('buildChartTooltipFormatter — standard (non-grouped)', () => {
    const fmt = buildChartTooltipFormatter({
        isGrouped: false,
        data,
        groupedSeries: [],
        totalCount: 10,
        hasActiveFilter: false
    });

    it('returns empty string for empty params', () => {
        expect(fmt([])).toBe('');
    });

    it('shows label, count, and percentage', () => {
        const result = fmt([param('car', 6)]);
        expect(result).toBe('<b>car</b><br/>Count: <b>6</b> (60.0%)');
    });

    it('shows 0 count when the category is not found in data', () => {
        const result = fmt([param('unknown', 0)]);
        expect(result).toBe('<b>unknown</b><br/>Count: <b>0</b> (0.0%)');
    });

    it('omits percentage when totalCount is 0', () => {
        const fmt0 = buildChartTooltipFormatter({
            isGrouped: false,
            data,
            groupedSeries: [],
            totalCount: 0,
            hasActiveFilter: false
        });
        const result = fmt0([param('car', 6)]);
        expect(result).toBe('<b>car</b><br/>Count: <b>6</b>');
    });

    it('escapes HTML in the category label', () => {
        const xssData: CategoryCount[] = [{ label: '<script>alert(1)</script>', count: 1 }];
        const fmtXss = buildChartTooltipFormatter({
            isGrouped: false,
            data: xssData,
            groupedSeries: [],
            totalCount: 1,
            hasActiveFilter: false
        });
        const result = fmtXss([param('<script>alert(1)</script>', 1)]);
        expect(result).toBe(
            '<b>&lt;script&gt;alert(1)&lt;/script&gt;</b><br/>Count: <b>1</b> (100.0%)'
        );
    });

    it('looks up categories by id while displaying their label', () => {
        const categories: CategoryCount[] = [{ id: 'category-1', label: 'car', count: 6 }];
        const fmtById = buildChartTooltipFormatter({
            isGrouped: false,
            data: categories,
            groupedSeries: [],
            totalCount: 10,
            hasActiveFilter: false
        });

        expect(fmtById([param('category-1', 6)])).toBe('<b>car</b><br/>Count: <b>6</b> (60.0%)');
    });
});

describe('buildChartTooltipFormatter — standard with active filter', () => {
    it('shows filtered and total counts when filteredCount differs from count', () => {
        const filtered: CategoryCount[] = [{ label: 'car', count: 6, filteredCount: 2 }];
        const fmt = buildChartTooltipFormatter({
            isGrouped: false,
            data: filtered,
            groupedSeries: [],
            totalCount: 10,
            hasActiveFilter: true
        });
        const result = fmt([param('car', 2)]);
        expect(result).toBe('<b>car</b><br/>Count: <b>2</b> (20.0%) of <b>6</b> (60.0%) total');
    });

    it('does not show "of total" when filteredCount equals count', () => {
        const filtered: CategoryCount[] = [{ label: 'car', count: 6, filteredCount: 6 }];
        const fmt = buildChartTooltipFormatter({
            isGrouped: false,
            data: filtered,
            groupedSeries: [],
            totalCount: 10,
            hasActiveFilter: true
        });
        const result = fmt([param('car', 6)]);
        expect(result).toBe('<b>car</b><br/>Count: <b>6</b> (60.0%)');
    });

    it('does not show "of total" when filteredCount is absent', () => {
        const fmt = buildChartTooltipFormatter({
            isGrouped: false,
            data,
            groupedSeries: [],
            totalCount: 10,
            hasActiveFilter: true
        });
        const result = fmt([param('car', 6)]);
        expect(result).toBe('<b>car</b><br/>Count: <b>6</b> (60.0%)');
    });
});

describe('buildChartTooltipFormatter — grouped', () => {
    const fmt = buildChartTooltipFormatter({
        isGrouped: true,
        data: [],
        groupedSeries,
        totalCount: 0,
        hasActiveFilter: false
    });

    it('returns empty string for empty params', () => {
        expect(fmt([])).toBe('');
    });

    it('uses the category name as a bold header', () => {
        const result = fmt([param('car', 3, { seriesIndex: 0, seriesName: 'Reviewed' })]);
        expect(result).toBe('<b>car</b><br/>Reviewed: <b>3</b> (60.0%)');
    });

    it('shows each series name and its count', () => {
        const result = fmt([
            param('car', 3, { seriesIndex: 0, seriesName: 'Reviewed' }),
            param('car', 1, { seriesIndex: 1, seriesName: 'Priority' })
        ]);
        expect(result).toBe(
            '<b>car</b><br/>Reviewed: <b>3</b> (60.0%)<br/>Priority: <b>1</b> (10.0%)'
        );
    });

    it('uses totalCount as denominator when provided on the series', () => {
        // tag-b has totalCount: 10
        const result = fmt([param('car', 1, { seriesIndex: 1, seriesName: 'Priority' })]);
        expect(result).toBe('<b>car</b><br/>Priority: <b>1</b> (10.0%)');
    });

    it('sums series data as denominator when totalCount is absent', () => {
        // tag-a: 3 + 2 = 5 total; car count = 3 → 60%
        const result = fmt([param('car', 3, { seriesIndex: 0, seriesName: 'Reviewed' })]);
        expect(result).toBe('<b>car</b><br/>Reviewed: <b>3</b> (60.0%)');
    });

    it('shows 0 count for a series missing the hovered category', () => {
        // tag-b has no 'dog' entry
        const result = fmt([param('dog', 0, { seriesIndex: 1, seriesName: 'Priority' })]);
        expect(result).toBe('<b>dog</b><br/>Priority: <b>0</b> (0.0%)');
    });

    it('escapes HTML in the series name', () => {
        const xssSeries: CategoryCountSeries[] = [
            { id: 'x', label: '<img src=x onerror=alert(1)>', data: [{ label: 'car', count: 1 }] }
        ];
        const fmtXss = buildChartTooltipFormatter({
            isGrouped: true,
            data: [],
            groupedSeries: xssSeries,
            totalCount: 0,
            hasActiveFilter: false
        });
        const result = fmtXss([
            param('car', 1, { seriesIndex: 0, seriesName: '<img src=x onerror=alert(1)>' })
        ]);
        expect(result).toBe('<b>car</b><br/>&lt;img src=x onerror=alert(1)&gt;: <b>1</b> (100.0%)');
    });

    it('keeps duplicate labels distinct by category id', () => {
        const categories: CategoryCount[] = [
            { id: 'first', label: 'Missing', count: 4 },
            { id: 'second', label: 'Missing', count: 2 }
        ];
        const duplicateLabelSeries: CategoryCountSeries[] = [
            {
                id: 'tag-a',
                label: 'Reviewed',
                data: [
                    { id: 'first', label: 'Missing', count: 3 },
                    { id: 'second', label: 'Missing', count: 1 }
                ]
            }
        ];
        const fmtById = buildChartTooltipFormatter({
            isGrouped: true,
            data: categories,
            groupedSeries: duplicateLabelSeries,
            totalCount: 0,
            hasActiveFilter: false
        });

        expect(fmtById([param('first', 3, { seriesIndex: 0 })])).toBe(
            '<b>Missing</b><br/>: <b>3</b> (75.0%)'
        );
        expect(fmtById([param('second', 1, { seriesIndex: 0 })])).toBe(
            '<b>Missing</b><br/>: <b>1</b> (25.0%)'
        );
    });
});
