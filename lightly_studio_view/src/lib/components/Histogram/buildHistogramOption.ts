import type { EChartsCoreOption } from 'echarts/core';
import {
    CHART_AXIS_LABEL,
    CHART_LINE_COLOR,
    formatFloat,
    formatInteger,
    formatPercent
} from '$lib/utils';
import type { HistogramData, HistogramRange } from './types';

// Same accent as BarChart (the Lightly primary green, --color-lightly-primary).
const BAR_COLOR = '#3bd99f';
// Bins outside the selected range: dimmed but still legible against the panel.
const BAR_COLOR_DIMMED = '#4b5563';

// Gap between adjacent bins, in px. Carved out of each bin's right edge, so it
// is exactly this wide everywhere (the edges are snapped to integer pixels).
const BIN_GAP_PX = 1;

export interface HistogramOptionOptions {
    /**
     * Renders numeric axes: bin-edge values along the x-axis and counts along
     * the y-axis. Off by default for the inline filter-panel variant, where
     * the range slider underneath provides the x-scale and axis gutters would
     * break the bar ↔ slider alignment.
     */
    showAxes?: boolean;
}

/**
 * A bin is highlighted when its interior overlaps the selected range. Bin `i`
 * covers the half-open interval `[edges[i], edges[i + 1])`, so a range that
 * merely touches a bin's edge does not select it — selecting exactly one bin
 * highlights exactly one bar, not its neighbors.
 */
export function isBinInRange(binStart: number, binEnd: number, range: HistogramRange): boolean {
    // Zero-width bin (constant-valued field): compare inclusively.
    if (binStart === binEnd) {
        return binStart >= range.min && binStart <= range.max;
    }
    return binEnd > range.min && binStart < range.max;
}

// Minimal typings for the ECharts custom-series render callback (the full
// types live in echarts' internal type surface, not in echarts/core).
interface RenderItemParams {
    dataIndex: number;
}
interface RenderItemApi {
    value: (dimension: number) => number;
    coord: (point: [number, number]) => [number, number];
    size: (span: [number, number]) => [number, number];
    style: () => Record<string, unknown>;
}

/**
 * Draws one bin as a pixel-snapped rect with a uniform 1px gap to its right
 * neighbor. The built-in bar series computes fractional per-bar widths, and
 * canvas antialiasing turns those fractional boundaries into uneven hairline
 * seams. Rounding both edges of every bin to integers makes the bar widths and
 * the gaps between them consistent regardless of chart width.
 *
 * The x-axis is a value axis over bin indices, so bin `i` spans `[i, i + 1]`
 * and `api.coord` returns its left edge.
 */
export function renderHistogramBin(
    params: RenderItemParams,
    api: RenderItemApi
): Record<string, unknown> {
    const index = params.dataIndex;
    const count = api.value(1);
    const [leftX, topY] = api.coord([index, count]);
    const [, baseY] = api.coord([index, 0]);
    const [bandWidth] = api.size([1, 0]);

    const left = Math.round(leftX);
    const right = Math.round(leftX + bandWidth) - BIN_GAP_PX;
    const top = Math.round(topY);

    return {
        type: 'rect',
        shape: {
            x: left,
            y: top,
            // Never collapse below 1px, however narrow the bins get.
            width: Math.max(1, right - left),
            height: Math.round(baseY) - top
        },
        style: api.style()
    };
}

/**
 * Builds the ECharts option for a histogram (pass to `setOption`). By default
 * there is no axes chrome — the inline variant sits directly above a range
 * slider that provides the x-scale — and bars span the full width edge to
 * edge. Pass `showAxes: true` (distribution panel) to render bin-edge values
 * on the x-axis and counts on the y-axis.
 */
export function buildHistogramOption(
    data: HistogramData,
    range?: HistogramRange,
    options: HistogramOptionOptions = {}
): EChartsCoreOption {
    const { binEdges, counts } = data;
    const showAxes = options.showAxes ?? false;
    const totalCount = counts.reduce((sum, count) => sum + count, 0);
    const binCount = counts.length;
    const domainMin = binEdges[0];
    const domainMax = binEdges[binEdges.length - 1];

    const bins = counts.map((count, i) => ({
        start: binEdges[i],
        end: binEdges[i + 1],
        count
    }));

    // The x-axis runs over bin indices (bin `i` spans `[i, i + 1]`); ticks map
    // back to data values. Bins are equal-width, so linear interpolation lands
    // exactly on the bin edges for integer ticks.
    const indexToValue = (index: number): number =>
        domainMin + (index / binCount) * (domainMax - domainMin);

    return {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'line' },
            // The inline chart is only a few tens of px tall; let the tooltip
            // escape the canvas instead of being clipped by it.
            confine: false,
            formatter: (params: { dataIndex: number }[]) => {
                const bin = bins[params[0]?.dataIndex];
                if (!bin) return '';
                const percent = totalCount > 0 ? ` (${formatPercent(bin.count / totalCount)})` : '';
                return (
                    `<b>${formatFloat(bin.start)} – ${formatFloat(bin.end)}</b><br/>` +
                    `Count: <b>${formatInteger(bin.count)}</b>${percent}`
                );
            }
        },
        grid: showAxes
            ? // containLabel reserves gutters for the tick labels; the extra
              // right padding keeps the last x label from being clipped.
              { left: 4, right: 16, top: 8, bottom: 4, containLabel: true }
            : // Bars flush with the canvas edges so they align with the slider track.
              { left: 0, right: 0, top: 2, bottom: 0 },
        xAxis: {
            type: 'value' as const,
            min: 0,
            max: binCount,
            show: showAxes,
            axisLabel: {
                ...CHART_AXIS_LABEL,
                formatter: (index: number) => formatFloat(indexToValue(index))
            },
            axisLine: { lineStyle: { color: CHART_LINE_COLOR } },
            axisTick: { lineStyle: { color: CHART_LINE_COLOR } },
            splitLine: { show: false }
        },
        yAxis: {
            type: 'value' as const,
            show: showAxes,
            // Counts are whole numbers; avoid fractional tick labels.
            minInterval: 1,
            axisLabel: CHART_AXIS_LABEL,
            splitLine: { lineStyle: { color: CHART_LINE_COLOR } }
        },
        series: [
            {
                // Custom series so every bin renders as a pixel-snapped rect
                // (see `renderHistogramBin`).
                type: 'custom',
                renderItem: renderHistogramBin,
                encode: { x: 0, y: 1 },
                data: bins.map((bin, i) => ({
                    value: [i, bin.count],
                    itemStyle: {
                        color:
                            !range || isBinInRange(bin.start, bin.end, range)
                                ? BAR_COLOR
                                : BAR_COLOR_DIMMED
                    }
                }))
            }
        ]
    };
}
