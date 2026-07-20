import type { EChartsCoreOption } from 'echarts/core';
import { truncate } from 'lodash-es';
import {
    CHART_AXIS_LABEL,
    CHART_EMPHASIS,
    CHART_LINE_COLOR,
    CHART_TEXT_COLOR,
    formatPercent,
    getSeriesColor
} from '$lib/utils';
import type { ChartMode, ChartNormalize, ChartScale, ChartSeries } from './types';

// Single accent color (the Lightly primary green, --color-lightly-primary #3bd99f):
// per-class colors carry no meaning in a single count distribution, mirroring
// FiftyOne's histograms panel. Overlaid series use the shared series palette.
const DEFAULT_BAR_COLOR = 'rgba(59,217,159,0.85)';

/** Missing-value bucket; always pinned last on the category axis. */
const NONE_LABEL = '(none)';

/** Bar layout: 'vertical' bars grow upward, 'horizontal' bars grow rightward. */
export type BarChartOrientation = 'vertical' | 'horizontal';

/** Compact mean-marker label: integers as-is, otherwise two decimals, trimmed. */
function formatMean(value: number): string {
    if (Number.isInteger(value)) return String(value);
    return value.toFixed(2).replace(/\.?0+$/, '');
}

interface BuildEchartsOptionOptions {
    /**
     * Denominator for tooltip percentages in count mode with a single series.
     * Pass the sum over all categories when the series is a subset (e.g. top-N)
     * so percentages stay relative to the full dataset. Ignored when
     * `normalize` is 'percentage'.
     */
    totalCount?: number;
    /** Bar orientation (default 'vertical'). */
    orientation?: BarChartOrientation;
    /** Chart form (default 'bar'). */
    mode?: ChartMode;
    /** Count vs within-series percentage (default 'count'). */
    normalize?: ChartNormalize;
    /** Value-axis scale (default 'linear'). */
    scale?: ChartScale;
}

/**
 * Ordered union of every series' category labels. Order follows the series with
 * the most categories, then any labels only other series carry, with `(none)`
 * pinned last. All series in one metadata distribution share categories (same
 * key / same histogram edges), so this usually just echoes one series' order.
 */
export function unionCategories(series: ChartSeries[]): string[] {
    const base = series.reduce(
        (longest, current) => (current.data.length > longest.data.length ? current : longest),
        series[0] ?? { data: [] }
    );
    const ordered: string[] = [];
    const seen = new Set<string>();
    const push = (label: string) => {
        if (!seen.has(label)) {
            seen.add(label);
            ordered.push(label);
        }
    };
    base.data.forEach((item) => push(item.label));
    series.forEach((current) => current.data.forEach((item) => push(item.label)));

    const noneIndex = ordered.indexOf(NONE_LABEL);
    if (noneIndex !== -1) {
        ordered.splice(noneIndex, 1);
        ordered.push(NONE_LABEL);
    }
    return ordered;
}

/** Builds the ECharts option for a (possibly multi-series) distribution chart. */
export function buildEchartsOption(
    series: ChartSeries[],
    options: BuildEchartsOptionOptions = {}
): EChartsCoreOption {
    const orientation = options.orientation ?? 'vertical';
    const mode = options.mode ?? 'bar';
    const normalize = options.normalize ?? 'count';
    const scale = options.scale ?? 'linear';
    const isHorizontal = orientation === 'horizontal';
    const isPercent = normalize === 'percentage';
    const isLog = scale === 'log';
    const isMulti = series.length > 1;

    const categories = unionCategories(series);
    const totals = series.map((s) => s.data.reduce((sum, item) => sum + item.count, 0));

    // Align each series to the shared category order, normalizing within the
    // series when requested (differently-sized tags stay comparable).
    const seriesValues = series.map((s, index) => {
        const byLabel = new Map(s.data.map((item) => [item.label, item.count]));
        return categories.map((label) => {
            const count = byLabel.get(label) ?? 0;
            if (!isPercent) return count;
            return totals[index] > 0 ? (count / totals[index]) * 100 : 0;
        });
    });

    const categoryAxis = {
        type: 'category' as const,
        data: categories,
        axisLabel: {
            // Vertical layout rotates long labels so they don't overflow the
            // canvas edge (echarts containLabel ignores rotation); horizontal
            // layout has room for flat labels down the left gutter.
            rotate: isHorizontal ? 0 : 60,
            interval: 0,
            color: CHART_TEXT_COLOR,
            fontSize: 12,
            // Cap long labels on the axis; the tooltip still shows the full name.
            formatter: (label: string) => truncate(label, { length: 24, omission: '…' })
        },
        axisLine: { lineStyle: { color: CHART_LINE_COLOR } },
        axisTick: { alignWithLabel: true },
        // Keep the highest bar at the top when horizontal (data is pre-sorted).
        // Histograms keep their natural low→high bin order.
        inverse: isHorizontal && mode === 'bar'
    };

    const valueAxis = {
        // A log axis drops zero/negative values (they map to -Infinity), so bars
        // for empty categories simply don't render — acceptable for a count
        // distribution where the point of log scale is separating tall from short.
        type: isLog ? ('log' as const) : ('value' as const),
        axisLabel: isPercent ? { ...CHART_AXIS_LABEL, formatter: '{value}%' } : CHART_AXIS_LABEL,
        splitLine: { lineStyle: { color: CHART_LINE_COLOR } }
    };

    const totalCount =
        options.totalCount ?? series[0]?.data.reduce((sum, item) => sum + item.count, 0) ?? 0;

    const chartSeries = series.map((s, index) => {
        const color = s.color ?? (isMulti ? getSeriesColor(index) : DEFAULT_BAR_COLOR);
        const values = seriesValues[index];
        // A dashed line at the series mean, positioned by its fractional index on
        // the category axis (so it can sit between bins). Attached to the series so
        // it inherits the series color and appears only for series that carry one.
        const markLine = s.mean
            ? {
                  symbol: 'none' as const,
                  silent: true,
                  lineStyle: { color, type: 'dashed' as const, width: 1.5 },
                  label: {
                      formatter: `μ ${formatMean(s.mean.value)}`,
                      color,
                      position: isHorizontal
                          ? ('insideEndBottom' as const)
                          : ('insideEndTop' as const),
                      fontSize: 11
                  },
                  data: [
                      isHorizontal
                          ? { yAxis: s.mean.categoryIndex }
                          : { xAxis: s.mean.categoryIndex }
                  ]
              }
            : undefined;
        // Numeric histograms with several series read best as step density
        // curves; a single series stays a filled histogram.
        if (mode === 'histogram' && isMulti) {
            return {
                name: s.label,
                type: 'line' as const,
                step: 'middle' as const,
                symbol: 'none' as const,
                data: values,
                lineStyle: { color, width: 2 },
                itemStyle: { color },
                emphasis: CHART_EMPHASIS,
                ...(markLine ? { markLine } : {})
            };
        }
        return {
            name: s.label,
            type: 'bar' as const,
            data: values,
            itemStyle: { color },
            // Touching bars read as a histogram; grouped bars keep a gap.
            barCategoryGap: mode === 'histogram' ? '0%' : '25%',
            emphasis: CHART_EMPHASIS,
            ...(markLine ? { markLine } : {})
        };
    });

    return {
        backgroundColor: 'transparent',
        legend: isMulti
            ? {
                  data: series.map((s) => s.label),
                  textStyle: { color: CHART_TEXT_COLOR },
                  top: 0
              }
            : undefined,
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: mode === 'histogram' && isMulti ? 'line' : 'shadow' },
            formatter: (
                params: { name: string; value: number; seriesName?: string; marker?: string }[]
            ) => {
                const name = params[0]?.name ?? '';
                const lines = params.map((param) => {
                    const prefix = `${param.marker ?? ''}${
                        param.seriesName ? `${param.seriesName}: ` : 'Count: '
                    }`;
                    if (isPercent) {
                        return `${prefix}<b>${param.value.toFixed(1)}%</b>`;
                    }
                    // Count mode: bold the number, keep the share (single series) outside.
                    const suffix =
                        !isMulti && totalCount > 0
                            ? ` (${formatPercent(param.value / totalCount)})`
                            : '';
                    return `${prefix}<b>${param.value}</b>${suffix}`;
                });
                return `<b>${name}</b><br/>${lines.join('<br/>')}`;
            }
        },
        grid: { left: 8, right: 8, top: isMulti ? 32 : 16, bottom: 8, containLabel: true },
        // Swap which axis holds the categories so bars grow rightward when horizontal.
        xAxis: isHorizontal ? valueAxis : categoryAxis,
        yAxis: isHorizontal ? categoryAxis : valueAxis,
        series: chartSeries
    };
}
