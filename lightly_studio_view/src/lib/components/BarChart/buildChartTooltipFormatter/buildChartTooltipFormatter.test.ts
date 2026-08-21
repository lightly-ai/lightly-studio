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
    const fmt = buildChartTooltipFormatter(false, data, [], 10, false);

    it('returns empty string for empty params', () => {
        expect(fmt([])).toBe('');
    });

    it('shows label, count, and percentage', () => {
        const result = fmt([param('car', 6)]);
        expect(result).toContain('<b>car</b>');
        expect(result).toContain('<b>6</b>');
        expect(result).toContain('60.0%');
    });

    it('shows 0 count when the category is not found in data', () => {
        const result = fmt([param('unknown', 0)]);
        expect(result).toContain('<b>0</b>');
    });

    it('omits percentage when totalCount is 0', () => {
        const fmt0 = buildChartTooltipFormatter(false, data, [], 0, false);
        const result = fmt0([param('car', 6)]);
        expect(result).not.toContain('%');
    });

    it('escapes HTML in the category label', () => {
        const xssData: CategoryCount[] = [{ label: '<script>alert(1)</script>', count: 1 }];
        const fmtXss = buildChartTooltipFormatter(false, xssData, [], 1, false);
        const result = fmtXss([param('<script>alert(1)</script>', 1)]);
        expect(result).not.toContain('<script>');
    });

    it('looks up categories by id while displaying their label', () => {
        const categories: CategoryCount[] = [{ id: 'category-1', label: 'car', count: 6 }];
        const fmtById = buildChartTooltipFormatter(false, categories, [], 10, false);

        expect(fmtById([param('category-1', 6)])).toContain('<b>car</b>');
        expect(fmtById([param('category-1', 6)])).toContain('<b>6</b>');
    });
});

describe('buildChartTooltipFormatter — standard with active filter', () => {
    it('shows filtered and total counts when filteredCount differs from count', () => {
        const filtered: CategoryCount[] = [{ label: 'car', count: 6, filteredCount: 2 }];
        const fmt = buildChartTooltipFormatter(false, filtered, [], 10, true);
        const result = fmt([param('car', 2)]);
        expect(result).toContain('of');
        expect(result).toContain('<b>2</b>');
        expect(result).toContain('<b>6</b>');
    });

    it('does not show "of total" when filteredCount equals count', () => {
        const filtered: CategoryCount[] = [{ label: 'car', count: 6, filteredCount: 6 }];
        const fmt = buildChartTooltipFormatter(false, filtered, [], 10, true);
        const result = fmt([param('car', 6)]);
        expect(result).not.toContain('of');
    });

    it('does not show "of total" when filteredCount is absent', () => {
        const fmt = buildChartTooltipFormatter(false, data, [], 10, true);
        const result = fmt([param('car', 6)]);
        expect(result).not.toContain('of');
    });
});

describe('buildChartTooltipFormatter — grouped', () => {
    const fmt = buildChartTooltipFormatter(true, [], groupedSeries, 0, false);

    it('returns empty string for empty params', () => {
        expect(fmt([])).toBe('');
    });

    it('uses the category name as a bold header', () => {
        const result = fmt([param('car', 3, { seriesIndex: 0, seriesName: 'Reviewed' })]);
        expect(result.startsWith('<b>car</b>')).toBe(true);
    });

    it('shows each series name and its count', () => {
        const result = fmt([
            param('car', 3, { seriesIndex: 0, seriesName: 'Reviewed' }),
            param('car', 1, { seriesIndex: 1, seriesName: 'Priority' })
        ]);
        expect(result).toContain('Reviewed');
        expect(result).toContain('Priority');
        expect(result).toContain('<b>3</b>');
        expect(result).toContain('<b>1</b>');
    });

    it('uses totalCount as denominator when provided on the series', () => {
        // tag-b has totalCount: 10
        const result = fmt([param('car', 1, { seriesIndex: 1, seriesName: 'Priority' })]);
        expect(result).toContain('10.0%'); // 1/10
    });

    it('sums series data as denominator when totalCount is absent', () => {
        // tag-a: 3 + 2 = 5 total; car count = 3 → 60%
        const result = fmt([param('car', 3, { seriesIndex: 0, seriesName: 'Reviewed' })]);
        expect(result).toContain('60.0%');
    });

    it('shows 0 count for a series missing the hovered category', () => {
        // tag-b has no 'dog' entry
        const result = fmt([param('dog', 0, { seriesIndex: 1, seriesName: 'Priority' })]);
        expect(result).toContain('<b>0</b>');
    });

    it('escapes HTML in the series name', () => {
        const xssSeries: CategoryCountSeries[] = [
            { id: 'x', label: '<img src=x onerror=alert(1)>', data: [{ label: 'car', count: 1 }] }
        ];
        const fmtXss = buildChartTooltipFormatter(true, [], xssSeries, 0, false);
        const result = fmtXss([
            param('car', 1, { seriesIndex: 0, seriesName: '<img src=x onerror=alert(1)>' })
        ]);
        expect(result).not.toContain('<img');
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
        const fmtById = buildChartTooltipFormatter(
            true,
            categories,
            duplicateLabelSeries,
            0,
            false
        );

        expect(fmtById([param('first', 3, { seriesIndex: 0 })])).toContain('<b>3</b>');
        expect(fmtById([param('second', 1, { seriesIndex: 0 })])).toContain('<b>1</b>');
    });
});
