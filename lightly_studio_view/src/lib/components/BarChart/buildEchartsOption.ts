import type { EChartsCoreOption } from 'echarts/core';
import escape from 'lodash-es/escape';
import { truncate } from 'lodash-es';
import {
    CHART_AXIS_LABEL,
    CHART_EMPHASIS,
    CHART_LINE_COLOR,
    CHART_TEXT_COLOR,
    formatPercent
} from '$lib/utils';
import type { CategoryCount, CategoryCountSeries } from './';

// Same accent as Histogram (the Lightly primary green, --color-lightly-primary #3bd99f).
const BAR_COLOR = 'rgba(59,217,159,0.85)';
// Bars not in the active selection render dimmed, matching the histogram behaviour.
const BAR_COLOR_DIMMED = '#4b5563';
// Full-dataset context bars drawn behind the filtered foreground bars.
// Matches CHART_LINE_COLOR so background bars blend with the chart grid lines.
const BAR_COLOR_BACKGROUND = '#374151';
const SERIES_COLORS = [
    '#4E79A7',
    '#F28E2B',
    '#59A14F',
    '#E15759',
    '#B07AA1',
    '#76B7B2',
    '#EDC948',
    '#FF9DA7',
    '#9C755F'
];

/** Maps a stable series ID to the same accessible chart colour across renders. */
export function colorForSeries(id: string): string {
    const hash = [...id].reduce((value, character) => value * 31 + character.charCodeAt(0), 0);
    return SERIES_COLORS[Math.abs(hash) % SERIES_COLORS.length];
}

/** Bar layout: 'vertical' bars grow upward, 'horizontal' bars grow rightward. */
export type BarChartOrientation = 'vertical' | 'horizontal';
export type BarChartValueMode = 'number' | 'percentage';

interface BuildEchartsOptionOptions {
    /**
     * Denominator for tooltip percentages. Pass the sum over all categories
     * when `data` is a subset (e.g. top-N), so percentages stay relative to
     * the full dataset. Defaults to the sum of `data`.
     */
    totalCount?: number;
    /** Bar orientation (default 'vertical'). */
    orientation?: BarChartOrientation;
    /** Top chart-grid padding in px (default 16). */
    gridTopPx?: number;
    /** Named grouped-bar series rendered instead of the single `data` series. */
    series?: CategoryCountSeries[];
    /** Whether bars show raw counts or each series' percentage distribution. */
    valueMode?: BarChartValueMode;
}

interface TooltipParam {
    name: string;
    value: number;
    seriesName?: string;
    seriesIndex?: number;
    marker?: string;
}

const formatTooltipValue = (count: number, total: number): string => {
    const percent = total > 0 ? ` (${formatPercent(count / total)})` : '';
    return `<b>${count}</b>${percent}`;
};

/** Builds the ECharts option for a category-count bar chart (pass to `setOption`). */
export function buildEchartsOption(
    data: CategoryCount[],
    options: BuildEchartsOptionOptions = {}
): EChartsCoreOption {
    const totalCount = options.totalCount ?? data.reduce((sum, item) => sum + item.count, 0);
    const orientation = options.orientation ?? 'vertical';
    const gridTopPx = options.gridTopPx ?? 16;
    const isHorizontal = orientation === 'horizontal';
    const groupedSeries = options.series ?? [];
    const isGrouped = groupedSeries.length > 0;
    const valueMode = options.valueMode ?? 'number';

    const labels = data.map((item) => item.label);
    // When any category is actively selected, dim the rest — mirrors the range
    // highlighting in the numeric Histogram where out-of-range bins go grey.
    const hasAnySelected = data.some((item) => item.selected === true);
    // Render a grey background bar at the full count when sidebar filters reduce
    // some bars below their unfiltered height. This keeps the original distribution
    // visible as context while the foreground bar communicates the filtered portion.
    const hasActiveFilter = data.some(
        (item) => item.filteredCount !== undefined && item.filteredCount !== item.count
    );

    const categoryAxis = {
        type: 'category' as const,
        data: labels,
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
        inverse: isHorizontal
    };

    const valueAxis = {
        type: 'value' as const,
        // Counts are whole numbers, so keep ticks on integer boundaries. Without
        // this, a max count of 1 makes ECharts split [0,1] into 0.2 steps and
        // render fractional labels (0, 0.2, 0.4 …).
        minInterval: valueMode === 'number' ? 1 : undefined,
        max: valueMode === 'percentage' ? 100 : undefined,
        axisLabel:
            valueMode === 'percentage'
                ? { ...CHART_AXIS_LABEL, formatter: (value: number) => `${value}%` }
                : CHART_AXIS_LABEL,
        splitLine: { lineStyle: { color: CHART_LINE_COLOR } }
    };

    const toChartValue = (count: number, denominator: number): number =>
        valueMode === 'percentage' && denominator > 0 ? (count / denominator) * 100 : count;

    // Foreground bar: coloured at the filtered count (or full count when no filter).
    const foregroundData = data.map((item) => {
        // Simple items with no selection/filter state can be returned as raw numbers,
        // which ECharts renders without per-item itemStyle overhead.
        if (item.selected == null && item.selectable == null && item.filteredCount == null) {
            return toChartValue(item.count, totalCount);
        }
        const foregroundCount =
            hasActiveFilter && item.filteredCount !== undefined ? item.filteredCount : item.count;
        const isDimmed = hasAnySelected && !item.selected;
        return {
            value: toChartValue(foregroundCount, totalCount),
            itemStyle: {
                color: isDimmed ? BAR_COLOR_DIMMED : BAR_COLOR,
                opacity: item.selectable === false ? 0.45 : 1
            }
        };
    });

    const foregroundSeries = {
        type: 'bar',
        data: foregroundData,
        itemStyle: { color: BAR_COLOR },
        barCategoryGap: '25%',
        // Overlay on top of the background series (barGap: '-100%' makes the bar
        // occupy the same slot as the preceding series instead of shifting right).
        ...(hasActiveFilter ? { barGap: '-100%' } : {}),
        emphasis: CHART_EMPHASIS
    };

    // Background series: full (unfiltered) count, always grey — only rendered
    // when the filter is active and at least one bar is visibly reduced.
    const backgroundSeries = hasActiveFilter
        ? {
              type: 'bar',
              data: data.map((item) => ({
                  value: toChartValue(item.count, totalCount),
                  itemStyle: {
                      color: BAR_COLOR_BACKGROUND,
                      opacity: item.selectable === false ? 0.45 : 1
                  }
              })),
              barCategoryGap: '25%',
              // Suppress hover highlight on the background so emphasis styling
              // (colour change, scale) only fires on the foreground bars.
              emphasis: { disabled: true }
          }
        : null;

    const standardSeries = hasActiveFilter
        ? [backgroundSeries, foregroundSeries]
        : [foregroundSeries];
    const chartSeries = isGrouped
        ? groupedSeries.map((item) => {
              const countsByLabel = new Map(
                  item.data.map((count) => [count.label, count.count])
              );
              const seriesTotal =
                  item.totalCount ?? item.data.reduce((sum, count) => sum + count.count, 0);
              return {
                  id: item.id,
                  name: item.label,
                  type: 'bar',
                  data: labels.map((label) =>
                      toChartValue(countsByLabel.get(label) ?? 0, seriesTotal)
                  ),
                  itemStyle: { color: colorForSeries(item.id) },
                  barCategoryGap: '25%',
                  emphasis: CHART_EMPHASIS
              };
          })
        : standardSeries;

    return {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            appendTo: 'body',
            formatter: (params: TooltipParam[]) => {
                if (params.length === 0) return '';
                const [{ name }] = params;
                if (isGrouped) {
                    const values = params
                        .map((item, index) => {
                            const series = groupedSeries[item.seriesIndex ?? index];
                            const count =
                                series?.data.find((entry) => entry.label === name)?.count ?? 0;
                            const seriesTotal =
                                series?.totalCount ??
                                series?.data.reduce((sum, entry) => sum + entry.count, 0) ??
                                0;
                            return `${item.marker ?? ''}${escape(item.seriesName ?? '')}: ${formatTooltipValue(count, seriesTotal)}`;
                        })
                        .join('<br/>');
                    return `<b>${escape(name)}</b><br/>${values}`;
                }
                const count = data.find((entry) => entry.label === name)?.count ?? 0;
                return `<b>${escape(name)}</b><br/>Count: ${formatTooltipValue(count, totalCount)}`;
            }
        },
        legend: isGrouped
            ? { type: 'scroll', top: 0, textStyle: { color: CHART_TEXT_COLOR } }
            : undefined,
        grid: { left: 8, right: 8, top: isGrouped ? 48 : gridTopPx, bottom: 8, containLabel: true },
        // Swap which axis holds the categories so bars grow rightward when horizontal.
        xAxis: isHorizontal ? valueAxis : categoryAxis,
        yAxis: isHorizontal ? categoryAxis : valueAxis,
        series: chartSeries
    };
}
