import { describe, expect, it } from 'vitest';
import * as echarts from 'echarts/core';
import { CustomChart } from 'echarts/charts';
import { GridComponent, TooltipComponent } from 'echarts/components';
import { SVGRenderer } from 'echarts/renderers';
import { buildHistogramOption, isBinInRange, renderHistogramBin } from './buildHistogramOption';
import { normal, singleBin } from './fixtures';

echarts.use([CustomChart, GridComponent, TooltipComponent, SVGRenderer]);

// echarts measures label text through a canvas 2d context that jsdom doesn't
// implement; stub the one method it needs so `setOption` stays quiet. Text
// layout has no bearing on the data-space snapping assertion below.
HTMLCanvasElement.prototype.getContext = (() => ({
    measureText: (text: string) => ({ width: text.length * 6 })
})) as unknown as typeof HTMLCanvasElement.prototype.getContext;

const ACCENT = '#3bd99f';
const DIMMED = '#4b5563';

type Option = ReturnType<typeof buildHistogramOption>;

interface BarDatum {
    value: [number, number];
    itemStyle: { color: string };
}

const getBars = (option: Option): BarDatum[] => (option.series as { data: BarDatum[] }[])[0].data;
const getColors = (option: Option): string[] => getBars(option).map((bar) => bar.itemStyle.color);
const getTooltipFormatter = (option: Option): ((params: { dataIndex: number }[]) => string) =>
    (option.tooltip as { formatter: (params: { dataIndex: number }[]) => string }).formatter;

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
    it('maps every bin count to a bar centered on its bin', () => {
        // x is the bin center (index + 0.5) so the axis tooltip snaps to the bar
        // under the cursor rather than to the next bin past a bar's midpoint.
        const bars = getBars(buildHistogramOption(normal));
        expect(bars.map((bar) => bar.value)).toEqual(
            normal.counts.map((count, i) => [i + 0.5, count])
        );
    });

    it('renders all bins in the accent color when no range is given', () => {
        expect(getColors(buildHistogramOption(normal)).every((c) => c === ACCENT)).toBe(true);
    });

    it('dims bins outside the selected range', () => {
        // Bins cover [0,5), [5,10) … [95,100]; range [20, 40] spans bins 4..7.
        const colors = getColors(buildHistogramOption(normal, { min: 20, max: 40 }));
        expect(colors[3]).toBe(DIMMED); // [15,20) only touches min
        expect(colors[4]).toBe(ACCENT);
        expect(colors[5]).toBe(ACCENT);
        expect(colors[7]).toBe(ACCENT);
        expect(colors[8]).toBe(DIMMED); // [40,45) only touches max
    });

    it('highlights exactly one bar when the range is a single bin', () => {
        // Range [10, 15] = bin 2 exactly.
        const colors = getColors(buildHistogramOption(normal, { min: 10, max: 15 }));
        expect(colors.filter((c) => c === ACCENT)).toEqual([ACCENT]);
        expect(colors[2]).toBe(ACCENT);
    });

    it('highlights everything when the range spans the full domain', () => {
        expect(
            getColors(buildHistogramOption(normal, { min: 0, max: 100 })).every((c) => c === ACCENT)
        ).toBe(true);
    });

    it('handles the single-bin constant-value case', () => {
        expect(getColors(buildHistogramOption(singleBin, { min: 42, max: 42 }))).toEqual([ACCENT]);
    });

    it('formats the tooltip with bin interval, count and percentage', () => {
        const html = getTooltipFormatter(buildHistogramOption(normal))([{ dataIndex: 9 }]);
        expect(html).toContain('45');
        expect(html).toContain('50');
        expect(html).toContain('%');
    });

    it('returns an empty tooltip for an out-of-range data index', () => {
        expect(getTooltipFormatter(buildHistogramOption(normal))([{ dataIndex: 999 }])).toBe('');
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

describe('axis tooltip snapping', () => {
    // Exercises the real ECharts pointer resolution rather than just the
    // encoding: for a value axis, axisTrigger.js resolves a hover with
    // `series.indicesOfNearest(axisDim, dim, value, null)`, so we call the same
    // API. The nearest data point to any x inside bin k must be bin k — which
    // holds only because the data is centered (index + 0.5); a left-edge
    // encoding would snap right-half hovers to the next bin.
    it('resolves a hover anywhere in a bar to that bar, not its neighbor', () => {
        const dom = document.createElement('div');
        const chart = echarts.init(dom, null, { renderer: 'svg', width: 800, height: 300 });
        chart.setOption(buildHistogramOption(normal));

        // getModel/getSeriesByIndex are internal, untyped echarts APIs.
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const series = (chart as any).getModel().getSeriesByIndex(0);
        // Sample near both edges of the first, a middle, and the last bin; the
        // right-half values (x.7) are the ones a left-edge encoding misresolved.
        for (const axisValue of [0.2, 0.7, 3.2, 3.7, 19.2, 19.7]) {
            const [nearest] = series.indicesOfNearest('x', 'x', axisValue, null);
            expect(nearest).toBe(Math.floor(axisValue));
        }

        chart.dispose();
    });
});

describe('renderHistogramBin', () => {
    interface Rect {
        shape: { x: number; y: number; width: number; height: number };
        style: { fill: string };
    }

    // Fake render API: `binCount` bins over a 100px-wide grid. The x-axis is a
    // value axis over bin indices, so `coord` maps index i to the bin's left
    // edge; count 0 sits at y=50 and counts map to y = 50 - count. value(0) is
    // the bin center (index + 0.5), matching how `buildSeries` encodes the data.
    const renderBin = (binIndex: number, count: number, binCount = 3): Rect => {
        const band = 100 / binCount;
        return renderHistogramBin(null, {
            value: (dimension: number) => (dimension === 1 ? count : binIndex + 0.5),
            coord: ([index, value]: [number, number]): [number, number] => [
                index * band,
                50 - value
            ],
            size: (): [number, number] => [band, 0],
            visual: () => ACCENT
        }) as unknown as Rect;
    };

    it('snaps every rect edge to an integer pixel', () => {
        const { shape } = renderBin(1, 10);
        expect(Object.values(shape).every(Number.isInteger)).toBe(true);
    });

    it('leaves a uniform 1px gap between adjacent bins', () => {
        const first = renderBin(0, 5);
        const second = renderBin(1, 8);
        expect(second.shape.x - (first.shape.x + first.shape.width)).toBe(1);
    });

    it('never collapses a bin below 1px width', () => {
        // 200 bins over 100px: the band is narrower than the 1px gap.
        expect(renderBin(3, 5, 200).shape.width).toBeGreaterThanOrEqual(1);
    });

    it('applies the item style from the data', () => {
        expect(renderBin(0, 5).style.fill).toBe(ACCENT);
    });
});
