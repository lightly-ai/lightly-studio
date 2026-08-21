import { CHART_EMPHASIS } from '$lib/utils';
import type { CategoryCount, CategoryCountSeries } from '../types';

export const categoryKey = (item: CategoryCount) => item.id ?? item.label;

/** Builds the ECharts series array for a grouped (multi-series) bar chart. */
export function buildGroupedSeries(
    data: CategoryCount[],
    groupedSeries: CategoryCountSeries[],
    groupedColors: Map<string, string>,
    toChartValue: (count: number, denominator: number) => number
) {
    const categoryKeys = data.map(categoryKey);

    return groupedSeries.map((series) => {
        const countsByKey = new Map(series.data.map((entry) => [categoryKey(entry), entry.count]));
        const seriesTotal =
            series.totalCount ?? series.data.reduce((sum, entry) => sum + entry.count, 0);
        return {
            id: series.id,
            name: series.label,
            type: 'bar',
            data: categoryKeys.map((key) => toChartValue(countsByKey.get(key) ?? 0, seriesTotal)),
            itemStyle: {
                color: groupedColors.get(series.id),
                borderColor: 'rgba(255,255,255,0.75)',
                borderWidth: 1
            },
            barCategoryGap: '25%',
            emphasis: CHART_EMPHASIS
        };
    });
}
