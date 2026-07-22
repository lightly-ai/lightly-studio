import type { EChartsCoreOption } from 'echarts/core';
import { truncate } from 'lodash-es';
import {
    CHART_AXIS_LABEL,
    CHART_EMPHASIS,
    CHART_LINE_COLOR,
    CHART_TEXT_COLOR,
    formatPercent
} from '$lib/utils';
import type { CategoryCount } from './';

// Same accent as Histogram (the Lightly primary green, --color-lightly-primary #3bd99f).
const BAR_COLOR = 'rgba(59,217,159,0.85)';
// Bars not in the active selection render dimmed, matching the histogram behaviour.
const BAR_COLOR_DIMMED = '#4b5563';
// Full-dataset context bars drawn behind the filtered foreground bars.
// Matches CHART_LINE_COLOR so background bars blend with the chart grid lines.
const BAR_COLOR_BACKGROUND = '#374151';

/** Bar layout: 'vertical' bars grow upward, 'horizontal' bars grow rightward. */
export type BarChartOrientation = 'vertical' | 'horizontal';

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
}

/** Builds the ECharts option for a category-count bar chart (pass to `setOption`). */
export function buildEchartsOption(
    data: CategoryCount[],
    options: BuildEchartsOptionOptions = {}
): EChartsCoreOption {
    const totalCount = options.totalCount ?? data.reduce((sum, item) => sum + item.count, 0);
    const orientation = options.orientation ?? 'vertical';
    const gridTopPx = options.gridTopPx ?? 16;
    const isHorizontal = orientation === 'horizontal';

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
        minInterval: 1,
        axisLabel: CHART_AXIS_LABEL,
        splitLine: { lineStyle: { color: CHART_LINE_COLOR } }
    };

    // Tooltip shows "Total / In filter" when a filter is active and actually
    // reduces the hovered bar; otherwise shows the single "Count" line.
    const formatter = (params: { name: string; value: number }[]) => {
        if (params.length >= 2) {
            const totalValue = params[0].value; // background series = full count
            const filteredValue = params[1].value; // foreground series = filtered count
            if (totalValue !== filteredValue) {
                const totalPct =
                    totalCount > 0 ? ` (${formatPercent(totalValue / totalCount)})` : '';
                const filteredPct =
                    totalCount > 0 ? ` (${formatPercent(filteredValue / totalCount)})` : '';
                return `<b>${params[0].name}</b><br/>Total: <b>${totalValue}</b>${totalPct}<br/>In filter: <b>${filteredValue}</b>${filteredPct}`;
            }
        }
        const [{ name, value }] = params;
        const percent = totalCount > 0 ? ` (${formatPercent(value / totalCount)})` : '';
        return `<b>${name}</b><br/>Count: <b>${value}</b>${percent}`;
    };

    // Foreground bar: coloured at the filtered count (or full count when no filter).
    const foregroundData = data.map((item) => {
        // Simple items with no selection/filter state can be returned as raw numbers,
        // which ECharts renders without per-item itemStyle overhead.
        if (item.selected == null && item.selectable == null && item.filteredCount == null) {
            return item.count;
        }
        const foregroundCount =
            hasActiveFilter && item.filteredCount !== undefined
                ? item.filteredCount
                : item.count;
        const isDimmed = hasAnySelected && !item.selected;
        return {
            value: foregroundCount,
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
                  value: item.count,
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

    const series = hasActiveFilter ? [backgroundSeries, foregroundSeries] : [foregroundSeries];

    return {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            appendTo: 'body',
            formatter
        },
        grid: { left: 8, right: 8, top: gridTopPx, bottom: 8, containLabel: true },
        // Swap which axis holds the categories so bars grow rightward when horizontal.
        xAxis: isHorizontal ? valueAxis : categoryAxis,
        yAxis: isHorizontal ? categoryAxis : valueAxis,
        series
    };
}
