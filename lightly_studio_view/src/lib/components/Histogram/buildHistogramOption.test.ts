import { describe, expect, it } from 'vitest';
import { buildHistogramOption, isBinInRange, renderHistogramBin } from './buildHistogramOption';
import { normal, singleBin } from './fixtures';

const ACCENT = '#3bd99f';
const DIMMED = '#4b5563';

interface BarDatum {
    value: [number, number];
    itemStyle: { color: string };
}

const getSeriesData = (option: ReturnType<typeof buildHistogramOption>): BarDatum[] => {
    const series = option.series as { data: BarDatum[] }[];
    return series[0].data;
};

describe('isBinInRange', () => {
    it('includes bins fully inside the range', () => {
        expect(isBinInRange(10, 15, { min: 0, max: 100 })).toBe(true);
    });

    it('includes bins partially overlapping the range on either side', () => {
        expect(isBinInRange(0, 10, { min: 5, max: 100 })).toBe(true);
        expect(isBinInRange(90, 100, { min: 0, max: 95 })).toBe(true);
    });

    it('excludes bins that merely touch the range boundary', () => {
        // Bins are half-open [start, end): a shared edge is not an overlap, so
        // selecting exactly one bin does not highlight its neighbors.
        expect(isBinInRange(0, 5, { min: 5, max: 100 })).toBe(false);
        expect(isBinInRange(95, 100, { min: 0, max: 95 })).toBe(false);
    });

    it('excludes bins entirely outside the range', () => {
        expect(isBinInRange(0, 4, { min: 5, max: 100 })).toBe(false);
        expect(isBinInRange(96, 100, { min: 0, max: 95 })).toBe(false);
    });

    it('compares zero-width bins inclusively', () => {
        expect(isBinInRange(42, 42, { min: 42, max: 42 })).toBe(true);
        expect(isBinInRange(42, 42, { min: 0, max: 10 })).toBe(false);
    });
});

describe('buildHistogramOption', () => {
    it('maps every bin count to a bar', () => {
        const data = getSeriesData(buildHistogramOption(normal));
        expect(data.map((bar) => bar.value)).toEqual(normal.counts.map((count, i) => [i, count]));
    });

    it('renders all bins in the accent color when no range is given', () => {
        const data = getSeriesData(buildHistogramOption(normal));
        expect(data.every((bar) => bar.itemStyle.color === ACCENT)).toBe(true);
    });

    it('dims bins outside the selected range', () => {
        // Bins cover [0,5), [5,10) … [95,100]; range [20, 40] spans bins 4..7.
        const data = getSeriesData(buildHistogramOption(normal, { min: 20, max: 40 }));
        const colors = data.map((bar) => bar.itemStyle.color);
        expect(colors[3]).toBe(DIMMED); // [15,20) only touches min
        expect(colors[4]).toBe(ACCENT);
        expect(colors[5]).toBe(ACCENT);
        expect(colors[7]).toBe(ACCENT);
        expect(colors[8]).toBe(DIMMED); // [40,45) only touches max
    });

    it('highlights exactly one bar when the range is a single bin', () => {
        // Range [10, 15] = bin 2 exactly.
        const data = getSeriesData(buildHistogramOption(normal, { min: 10, max: 15 }));
        const accented = data.filter((bar) => bar.itemStyle.color === ACCENT);
        expect(accented).toHaveLength(1);
        expect(data[2].itemStyle.color).toBe(ACCENT);
    });

    it('highlights everything when the range spans the full domain', () => {
        const data = getSeriesData(buildHistogramOption(normal, { min: 0, max: 100 }));
        expect(data.every((bar) => bar.itemStyle.color === ACCENT)).toBe(true);
    });

    it('handles the single-bin constant-value case', () => {
        const data = getSeriesData(buildHistogramOption(singleBin, { min: 42, max: 42 }));
        expect(data).toHaveLength(1);
        expect(data[0].itemStyle.color).toBe(ACCENT);
    });

    it('formats the tooltip with bin interval, count and percentage', () => {
        const option = buildHistogramOption(normal);
        const tooltip = option.tooltip as {
            formatter: (params: { dataIndex: number }[]) => string;
        };
        const html = tooltip.formatter([{ dataIndex: 9 }]);
        expect(html).toContain('45');
        expect(html).toContain('50');
        expect(html).toContain('%');
    });

    it('returns an empty tooltip for an out-of-range data index', () => {
        const option = buildHistogramOption(normal);
        const tooltip = option.tooltip as {
            formatter: (params: { dataIndex: number }[]) => string;
        };
        expect(tooltip.formatter([{ dataIndex: 999 }])).toBe('');
    });

    it('hides both axes by default (inline variant)', () => {
        const option = buildHistogramOption(normal);
        expect((option.xAxis as { show: boolean }).show).toBe(false);
        expect((option.yAxis as { show: boolean }).show).toBe(false);
    });

    it('shows axes with bin-edge values when showAxes is set', () => {
        const option = buildHistogramOption(normal, undefined, { showAxes: true });
        const xAxis = option.xAxis as {
            show: boolean;
            axisLabel: { formatter: (index: number) => string };
        };
        expect(xAxis.show).toBe(true);
        expect((option.yAxis as { show: boolean }).show).toBe(true);
        // Integer ticks land exactly on bin edges: 0 → domain min, N → max.
        expect(xAxis.axisLabel.formatter(0)).toBe('0');
        expect(xAxis.axisLabel.formatter(10)).toBe('50');
        expect(xAxis.axisLabel.formatter(20)).toBe('100');
    });
});

describe('renderHistogramBin', () => {
    // Fake render API: 3 bins over a 100px-wide grid (fractional 33.33px band).
    // The x-axis is a value axis over bin indices, so `coord` maps index i to
    // the bin's left edge; count 0 sits at y=50 and counts map to y = 50 - count.
    const makeApi = (dataIndex: number, count: number) => ({
        value: (dimension: number) => (dimension === 1 ? count : dataIndex),
        coord: ([index, value]: [number, number]): [number, number] => [
            index * (100 / 3),
            50 - value
        ],
        size: (): [number, number] => [100 / 3, 0],
        style: () => ({ fill: ACCENT })
    });

    it('snaps both bin edges to integer pixels', () => {
        const rect = renderHistogramBin({ dataIndex: 1 }, makeApi(1, 10)) as {
            shape: { x: number; width: number; y: number; height: number };
        };
        expect(Number.isInteger(rect.shape.x)).toBe(true);
        expect(Number.isInteger(rect.shape.width)).toBe(true);
        expect(Number.isInteger(rect.shape.y)).toBe(true);
        expect(Number.isInteger(rect.shape.height)).toBe(true);
    });

    it('leaves a uniform 1px gap between adjacent bins', () => {
        const first = renderHistogramBin({ dataIndex: 0 }, makeApi(0, 5)) as {
            shape: { x: number; width: number };
        };
        const second = renderHistogramBin({ dataIndex: 1 }, makeApi(1, 8)) as {
            shape: { x: number; width: number };
        };
        expect(second.shape.x - (first.shape.x + first.shape.width)).toBe(1);
    });

    it('never collapses a bin below 1px width', () => {
        // 200 bins over 100px: the band is narrower than the 1px gap.
        const narrowApi = (dataIndex: number, count: number) => ({
            value: (dimension: number) => (dimension === 1 ? count : dataIndex),
            coord: ([index, value]: [number, number]): [number, number] => [
                index * (100 / 200),
                50 - value
            ],
            size: (): [number, number] => [100 / 200, 0],
            style: () => ({ fill: ACCENT })
        });
        const rect = renderHistogramBin({ dataIndex: 3 }, narrowApi(3, 5)) as {
            shape: { width: number };
        };
        expect(rect.shape.width).toBeGreaterThanOrEqual(1);
    });

    it('applies the item style from the data', () => {
        const rect = renderHistogramBin({ dataIndex: 0 }, makeApi(0, 5)) as {
            style: { fill: string };
        };
        expect(rect.style.fill).toBe(ACCENT);
    });
});
