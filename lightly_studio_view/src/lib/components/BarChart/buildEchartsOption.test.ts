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

    it('shows the percentage of the data sum in the tooltip', () => {
        const formatter = getFormatter(
            buildEchartsOption([
                { label: 'car', count: 25 },
                { label: 'dog', count: 75 }
            ])
        );

        expect(formatter([{ name: 'car', value: 25 }])).toBe(
            '<b>car</b><br/>Count: <b>25</b> (25.0%)'
        );
    });

    it('uses the provided totalCount as the percentage denominator', () => {
        const formatter = getFormatter(
            buildEchartsOption([{ label: 'car', count: 25 }], { totalCount: 1000 })
        );

        expect(formatter([{ name: 'car', value: 25 }])).toBe(
            '<b>car</b><br/>Count: <b>25</b> (2.5%)'
        );
    });

    it('renders tiny shares as <0.1% and omits percentages for an empty total', () => {
        const small = getFormatter(
            buildEchartsOption([{ label: 'car', count: 1 }], { totalCount: 10000 })
        );
        expect(small([{ name: 'car', value: 1 }])).toBe('<b>car</b><br/>Count: <b>1</b> (<0.1%)');

        const empty = getFormatter(buildEchartsOption([]));
        expect(empty([{ name: 'car', value: 0 }])).toBe('<b>car</b><br/>Count: <b>0</b>');
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
