import { describe, expect, it } from 'vitest';
import { buildEchartsOption } from './buildEchartsOption';
import { balanced } from './fixtures';

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
                tooltip: { formatter: (params: { name: string; value: number }[]) => string };
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
});
