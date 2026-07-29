import { describe, expect, it } from 'vitest';
import { buildTooltipFormatter } from './buildTooltipFormatter';

describe('buildTooltipFormatter', () => {
    it('shows the percentage of the data sum in the tooltip', () => {
        const formatter = buildTooltipFormatter(100);

        expect(formatter([{ name: 'car', value: 25 }])).toBe(
            '<b>car</b><br/>Count: <b>25</b> (25.0%)'
        );
    });

    it('uses the provided totalCount as the percentage denominator', () => {
        const formatter = buildTooltipFormatter(1000);

        expect(formatter([{ name: 'car', value: 25 }])).toBe(
            '<b>car</b><br/>Count: <b>25</b> (2.5%)'
        );
    });

    it('renders tiny shares as <0.1% and omits percentages for an empty total', () => {
        const small = buildTooltipFormatter(10000);
        expect(small([{ name: 'car', value: 1 }])).toBe('<b>car</b><br/>Count: <b>1</b> (<0.1%)');

        const empty = buildTooltipFormatter(0);
        expect(empty([{ name: 'car', value: 0 }])).toBe('<b>car</b><br/>Count: <b>0</b>');
    });

    it('shows Total / In filter when two series are present and counts differ', () => {
        const formatter = buildTooltipFormatter(200);

        expect(
            formatter([
                { name: 'dog', value: 100 },
                { name: 'dog', value: 60 }
            ])
        ).toBe('<b>dog</b><br/>Total: <b>100</b> (50.0%)<br/>In filter: <b>60</b> (30.0%)');
    });

    it('falls back to single Count line when two series have equal counts', () => {
        const formatter = buildTooltipFormatter(100);

        expect(
            formatter([
                { name: 'cat', value: 50 },
                { name: 'cat', value: 50 }
            ])
        ).toBe('<b>cat</b><br/>Count: <b>50</b> (50.0%)');
    });

    it('escapes HTML markup in category labels', () => {
        const formatter = buildTooltipFormatter(100);

        expect(formatter([{ name: '<script>alert(1)</script>', value: 10 }])).toBe(
            '<b>&lt;script&gt;alert(1)&lt;/script&gt;</b><br/>Count: <b>10</b> (10.0%)'
        );

        expect(
            formatter([
                { name: '<b>bold</b>', value: 80 },
                { name: '<b>bold</b>', value: 40 }
            ])
        ).toBe(
            '<b>&lt;b&gt;bold&lt;/b&gt;</b><br/>Total: <b>80</b> (80.0%)<br/>In filter: <b>40</b> (40.0%)'
        );
    });
});
