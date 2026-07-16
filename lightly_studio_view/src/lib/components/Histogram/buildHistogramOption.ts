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

/** A single bar: the half-open value interval `[start, end)` and its count. */
interface HistogramBin {
    start: number;
    end: number;
    count: number;
}

/** Inputs the x-axis needs to map integer bin indices back to domain values. */
interface HistogramAxisOptions {
    /** Number of bins; also the x-axis max (indices run `0..binCount`). */
    binCount: number;
    /** Left edge of the first bin (domain minimum). */
    domainMin: number;
    /** Right edge of the last bin (domain maximum). */
    domainMax: number;
    /** Whether axis chrome is rendered (see `HistogramOptionOptions.showAxes`). */
    showAxes: boolean;
}

/** Inputs the bar series needs: the bins and the optional highlight range. */
interface HistogramSeriesOptions {
    bins: HistogramBin[];
    /** Selected value range; bins outside it render dimmed. Omit to highlight all. */
    range?: HistogramRange;
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

// Minimal typings for the ECharts custom-series render callback (the full types
// live in echarts' internal type surface, not in echarts/core). ECharts calls
// `renderItem(params, api)`; we ignore `params` and read everything — including
// the bin center, which we encode as dimension 0 — through `api`.
interface RenderItemApi {
    /** Reads encoded dimension `d` of the current item (0 = bin center, 1 = count). */
    value: (dimension: number) => number;
    /** Maps a data-space point `[index, value]` to pixel coordinates `[x, y]`. */
    coord: (point: [number, number]) => [number, number];
    /** Maps a data-space span `[dx, dy]` to its pixel size `[width, height]`. */
    size: (span: [number, number]) => [number, number];
    /** Resolved visual for the current item; `'color'` returns its itemStyle fill. */
    visual: (visualType: string) => string;
}

/**
 * Draws one bin as a pixel-snapped rect with a uniform 1px gap to its right
 * neighbor. The built-in bar series computes fractional per-bar widths, and
 * canvas antialiasing turns those fractional boundaries into uneven hairline
 * seams. Rounding both edges of every bin to integers makes the bar widths and
 * the gaps between them consistent regardless of chart width.
 *
 * The x-axis is a value axis over bin indices. `api.value(0)` is the bin
 * *center* `i + 0.5` (see `buildSeries`), so we step back half a band to the
 * left edge `i`; bin `i` spans `[i, i + 1]` and `api.coord` maps it to pixels.
 */
export function renderHistogramBin(_params: unknown, api: RenderItemApi): Record<string, unknown> {
    const index = api.value(0) - 0.5;
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
        style: { fill: api.visual('color') }
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
    const bins = buildBins(data);
    const showAxes = options.showAxes ?? false;
    const axisOptions = {
        binCount: data.counts.length,
        domainMin: data.binEdges[0],
        domainMax: data.binEdges[data.binEdges.length - 1],
        showAxes
    };

    return {
        backgroundColor: 'transparent',
        tooltip: buildTooltip(bins),
        grid: buildGrid(showAxes),
        xAxis: buildXAxis(axisOptions),
        yAxis: buildYAxis(showAxes),
        series: buildSeries({ bins, range })
    };
}

/** Pairs each count with its bin's edges (`counts[i]` spans `binEdges[i..i+1]`). */
function buildBins(data: HistogramData): HistogramBin[] {
    return data.counts.map((count, index) => ({
        start: data.binEdges[index],
        end: data.binEdges[index + 1],
        count
    }));
}

/** Tooltip showing the hovered bin's interval, count, and share of the total. */
function buildTooltip(bins: HistogramBin[]): Record<string, unknown> {
    const totalCount = bins.reduce((sum, bin) => sum + bin.count, 0);
    return {
        trigger: 'axis',
        axisPointer: { type: 'line' },
        // Let the tooltip escape the short inline canvas instead of being clipped.
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
    };
}

/** Plot padding: gutters for labels when axes show, flush to the edges when not. */
function buildGrid(showAxes: boolean): Record<string, unknown> {
    // containLabel reserves gutters for labels; right padding avoids clipping.
    return showAxes
        ? { left: 4, right: 16, top: 8, bottom: 4, containLabel: true }
        : { left: 0, right: 0, top: 2, bottom: 0 };
}

/**
 * Value x-axis spanning `0..binCount`. Tick labels convert the integer bin
 * index back to a domain value, so edges read as real numbers, not indices.
 */
function buildXAxis(options: HistogramAxisOptions): Record<string, unknown> {
    const indexToValue = (index: number): number =>
        options.domainMin + (index / options.binCount) * (options.domainMax - options.domainMin);
    return {
        type: 'value',
        min: 0,
        max: options.binCount,
        show: options.showAxes,
        axisLabel: {
            ...CHART_AXIS_LABEL,
            formatter: (index: number) => formatFloat(indexToValue(index))
        },
        axisLine: { lineStyle: { color: CHART_LINE_COLOR } },
        axisTick: { lineStyle: { color: CHART_LINE_COLOR } },
        splitLine: { show: false }
    };
}

/** Value y-axis for counts, with whole-number ticks. */
function buildYAxis(showAxes: boolean): Record<string, unknown> {
    return {
        type: 'value',
        show: showAxes,
        // Counts are whole numbers; avoid fractional tick labels.
        minInterval: 1,
        axisLabel: CHART_AXIS_LABEL,
        splitLine: { lineStyle: { color: CHART_LINE_COLOR } }
    };
}

/**
 * The custom bar series: one pixel-snapped rect per bin (see
 * `renderHistogramBin`), each colored by whether it falls in the range.
 */
function buildSeries(options: HistogramSeriesOptions): Record<string, unknown>[] {
    return [
        {
            type: 'custom',
            renderItem: renderHistogramBin,
            encode: { x: 0, y: 1 },
            data: options.bins.map((bin, index) => ({
                // x is the bin *center* (index + 0.5), not the left edge, so the
                // axis-trigger tooltip snaps the pointer to the bar the cursor is
                // actually over. A left-edge point would snap to the next bin once
                // the cursor passed a bar's midpoint. `renderHistogramBin` steps
                // back half a band to recover the left edge for drawing.
                value: [index + 0.5, bin.count],
                itemStyle: {
                    color:
                        !options.range || isBinInRange(bin.start, bin.end, options.range)
                            ? BAR_COLOR
                            : BAR_COLOR_DIMMED
                }
            }))
        }
    ];
}
