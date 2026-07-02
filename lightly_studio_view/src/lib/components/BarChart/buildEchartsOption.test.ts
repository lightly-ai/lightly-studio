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
});
