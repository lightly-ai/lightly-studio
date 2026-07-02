import { describe, expect, it } from 'vitest';
import { buildEchartsOption, truncateLabel } from './buildEchartsOption';
import { balanced } from './fixtures';

describe('truncateLabel', () => {
    it('keeps short labels unchanged', () => {
        expect(truncateLabel('car')).toBe('car');
    });

    it('truncates labels longer than 24 characters with an ellipsis', () => {
        const label = 'construction_vehicle_articulated_dump_truck';
        const truncated = truncateLabel(label);
        expect(truncated).toHaveLength(24);
        expect(truncated.endsWith('…')).toBe(true);
    });
});

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
