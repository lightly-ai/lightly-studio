import { describe, expect, it } from 'vitest';
import { buildEchartsOption, colorForSeries } from './buildEchartsOption';
import type { CategoryCountSeries } from './types';
import { balanced } from './fixtures';

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

describe('buildEchartsOption', () => {
    it('maps labels to the category axis and counts to the bar series', () => {
        const option = buildEchartsOption(balanced) as {
            xAxis: { data: string[] };
            series: [{ type: string; data: number[] }];
        };

        expect(option.xAxis.data).toEqual(balanced.map((item) => item.label));
        expect(option.series[0].type).toBe('bar');
        expect(option.series[0].data).toEqual(balanced.map((item) => item.count));
    });

    it('puts categories on the value axis when horizontal, keeping the bar series', () => {
        const option = buildEchartsOption(balanced, { orientation: 'horizontal' }) as {
            xAxis: { type: string };
            yAxis: { type: string; data: string[]; inverse: boolean };
            series: [{ type: string; data: number[] }];
        };

        expect(option.xAxis.type).toBe('value');
        expect(option.yAxis.type).toBe('category');
        expect(option.yAxis.data).toEqual(balanced.map((item) => item.label));
        // Highest bar (first, pre-sorted) stays at the top.
        expect(option.yAxis.inverse).toBe(true);
        expect(option.series[0].data).toEqual(balanced.map((item) => item.count));
    });

    it('keeps the value axis on integer ticks so single-annotation classes avoid fractional labels', () => {
        const vertical = buildEchartsOption([{ label: 'kite', count: 1 }]) as {
            yAxis: { minInterval: number };
        };
        const horizontal = buildEchartsOption([{ label: 'kite', count: 1 }], {
            orientation: 'horizontal'
        }) as { xAxis: { minInterval: number } };

        expect(vertical.yAxis.minInterval).toBe(1);
        expect(horizontal.xAxis.minInterval).toBe(1);
    });

    const getFormatter = (option: unknown) =>
        (
            option as {
                tooltip: {
                    formatter: (
                        params: {
                            name: string;
                            value: number;
                            seriesName?: string;
                            marker?: string;
                        }[]
                    ) => string;
                };
            }
        ).tooltip.formatter;

    it('unselected bars are dimmed while the selected bar remains green', () => {
        const option = buildEchartsOption([
            { id: 'sel', label: 'Missing', count: 3, selected: true, selectable: true },
            { id: 'other', label: 'Other', count: 2, selected: false, selectable: false }
        ]) as {
            series: [{ data: { value: number; itemStyle: Record<string, unknown> }[] }];
        };

        // Selected bar: accent green, full opacity.
        expect(option.series[0].data[0]).toMatchObject({
            value: 3,
            itemStyle: { color: 'rgba(59,217,159,0.85)', opacity: 1 }
        });
        // Non-selected + non-selectable: dimmed colour and reduced opacity.
        expect(option.series[0].data[1]).toMatchObject({
            value: 2,
            itemStyle: { color: '#4b5563', opacity: 0.45 }
        });
    });

    it('overlays a filtered foreground bar on a grey full-count background when filteredCount differs', () => {
        const option = buildEchartsOption([
            { label: 'dog', count: 100, filteredCount: 60 },
            { label: 'cat', count: 50, filteredCount: 50 }
        ]) as {
            series: [
                { type: string; data: { value: number }[] },
                { type: string; data: { value: number }[]; barGap: string }
            ];
        };

        // Two series rendered when filter is active.
        expect(option.series).toHaveLength(2);
        // Background series: always full count.
        expect(option.series[0].data[0].value).toBe(100);
        expect(option.series[0].data[1].value).toBe(50);
        // Foreground series: filtered count; uses barGap '-100%' to overlay.
        expect(option.series[1].data[0]).toMatchObject({ value: 60 });
        expect(option.series[1].data[1]).toMatchObject({ value: 50 });
        expect(option.series[1].barGap).toBe('-100%');
    });

    it('renders a single series and no background when all filteredCounts match full counts', () => {
        const option = buildEchartsOption([
            { label: 'dog', count: 100, filteredCount: 100 },
            { label: 'cat', count: 50, filteredCount: 50 }
        ]) as { series: unknown[] };

        expect(option.series).toHaveLength(1);
    });

    it('accepts compact top padding without changing the default grid', () => {
        const standard = buildEchartsOption(balanced) as { grid: { top: number } };
        const compact = buildEchartsOption(balanced, { gridTopPx: 4 }) as {
            grid: { top: number };
        };

        expect(standard.grid.top).toBe(16);
        expect(compact.grid.top).toBe(4);
    });

    it('renders named grouped series on a shared axis and zero-fills missing values', () => {
        const option = buildEchartsOption(
            [
                { label: 'car', count: 4 },
                { label: 'dog', count: 0 }
            ],
            { series: groupedSeries }
        ) as {
            xAxis: { data: string[] };
            legend: { type: string };
            series: { name: string; data: number[]; itemStyle: { color: string } }[];
        };

        expect(option.xAxis.data).toEqual(['car', 'dog']);
        expect(option.legend.type).toBe('scroll');
        expect(option.series.map((series) => series.name)).toEqual(['Reviewed', 'Priority']);
        expect(option.series.map((series) => series.data)).toEqual([
            [3, 0],
            [1, 0]
        ]);
        expect(option.series[0].itemStyle.color).not.toBe(option.series[1].itemStyle.color);
    });

    it('supports grouped series with a horizontal category axis', () => {
        const option = buildEchartsOption([{ label: 'car', count: 4 }], {
            orientation: 'horizontal',
            series: groupedSeries
        }) as {
            xAxis: { type: string };
            yAxis: { type: string; data: string[] };
            series: { data: number[] }[];
        };

        expect(option.xAxis.type).toBe('value');
        expect(option.yAxis).toMatchObject({ type: 'category', data: ['car'] });
        expect(option.series.map((series) => series.data)).toEqual([[3], [1]]);
    });

    it('uses stable colours and identifies every series in grouped tooltips', () => {
        expect(colorForSeries('tag-a')).toBe(colorForSeries('tag-a'));
        expect(colorForSeries('tag-a')).not.toBe(colorForSeries('tag-b'));

        const formatter = getFormatter(
            buildEchartsOption([{ label: 'car', count: 4 }], { series: groupedSeries })
        );
        expect(
            formatter([
                { name: 'car', value: 3, seriesName: 'Reviewed', marker: '● ' },
                { name: 'car', value: 1, seriesName: 'Priority', marker: '■ ' }
            ])
        ).toBe('<b>car</b><br/>● Reviewed: <b>3</b><br/>■ Priority: <b>1</b>');
    });
});
