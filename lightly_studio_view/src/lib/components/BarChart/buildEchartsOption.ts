import type { EChartsCoreOption } from 'echarts/core';
import { truncate } from 'lodash-es';
import {
    CHART_AXIS_LABEL,
    CHART_EMPHASIS,
    CHART_LINE_COLOR,
    CHART_TEXT_COLOR,
    formatPercent
} from '$lib/utils';
import type { CategoryCount, CategoryCountSeries } from './';

// Single accent color (the Lightly primary green, --color-lightly-primary #3bd99f):
// per-class colors carry no meaning in a count distribution.
const BAR_COLOR = 'rgba(59,217,159,0.85)';
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

interface BuildEchartsOptionOptions {
    /**
     * Denominator for tooltip percentages. Pass the sum over all categories
     * when `data` is a subset (e.g. top-N), so percentages stay relative to
     * the full dataset. Defaults to the sum of `data`.
     */
    totalCount?: number;
    /** Bar orientation (default 'vertical'). */
    orientation?: BarChartOrientation;
    /** Named grouped-bar series rendered instead of the single `data` series. */
    series?: CategoryCountSeries[];
}

/** Builds the ECharts option for a category-count bar chart (pass to `setOption`). */
export function buildEchartsOption(
    data: CategoryCount[],
    options: BuildEchartsOptionOptions = {}
): EChartsCoreOption {
    const totalCount = options.totalCount ?? data.reduce((sum, item) => sum + item.count, 0);
    const orientation = options.orientation ?? 'vertical';
    const isHorizontal = orientation === 'horizontal';
    const groupedSeries = options.series ?? [];
    const isGrouped = groupedSeries.length > 0;

    const labels = data.map((item) => item.label);

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

    return {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: (
                params: { name: string; value: number; seriesName?: string; marker?: string }[]
            ) => {
                const [{ name, value }] = params;
                if (isGrouped) {
                    const values = params
                        .map(
                            (item) => `${item.marker ?? ''}${item.seriesName}: <b>${item.value}</b>`
                        )
                        .join('<br/>');
                    return `<b>${name}</b><br/>${values}`;
                }
                const percent = totalCount > 0 ? ` (${formatPercent(value / totalCount)})` : '';
                return `<b>${name}</b><br/>Count: <b>${value}</b>${percent}`;
            }
        },
        legend: isGrouped
            ? { type: 'scroll', top: 0, textStyle: { color: CHART_TEXT_COLOR } }
            : undefined,
        grid: { left: 8, right: 8, top: isGrouped ? 48 : 16, bottom: 8, containLabel: true },
        // Swap which axis holds the categories so bars grow rightward when horizontal.
        xAxis: isHorizontal ? valueAxis : categoryAxis,
        yAxis: isHorizontal ? categoryAxis : valueAxis,
        series: isGrouped
            ? groupedSeries.map((item) => {
                  const countsByLabel = new Map(
                      item.data.map((count) => [count.label, count.count])
                  );
                  return {
                      id: item.id,
                      name: item.label,
                      type: 'bar',
                      data: labels.map((label) => countsByLabel.get(label) ?? 0),
                      itemStyle: { color: colorForSeries(item.id) },
                      barCategoryGap: '25%',
                      emphasis: CHART_EMPHASIS
                  };
              })
            : [
                  {
                      type: 'bar',
                      data: data.map((item) => item.count),
                      itemStyle: { color: BAR_COLOR },
                      barCategoryGap: '25%',
                      emphasis: CHART_EMPHASIS
                  }
              ]
    };
}
