import escape from 'lodash-es/escape';
import { formatPercent } from '$lib/utils';
import type { CategoryCount, CategoryCountSeries } from '../types';
import { categoryKey } from '../buildGroupedSeries';

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

interface ChartTooltipFormatterOptions {
    /** Whether the chart displays grouped (multi-series) bars. */
    isGrouped: boolean;
    /** Flat category counts used for standard (non-grouped) tooltips. */
    data: CategoryCount[];
    /** Per-series category counts used for grouped tooltips. */
    groupedSeries: CategoryCountSeries[];
    /** Total sample count used as the percentage denominator. */
    totalCount: number;
    /** Whether a dataset filter is currently active, enabling filtered vs. total display. */
    hasActiveFilter: boolean;
}

/** Builds the ECharts tooltip formatter for grouped or standard bar charts. */
export function buildChartTooltipFormatter({
    isGrouped,
    data,
    groupedSeries,
    totalCount,
    hasActiveFilter
}: ChartTooltipFormatterOptions): (params: TooltipParam[]) => string {
    return (params: TooltipParam[]) => {
        if (params.length === 0) return '';
        const [{ name }] = params;
        const category = data.find((entry) => categoryKey(entry) === name);
        const header = `<b>${escape(category?.label ?? name)}</b>`;

        if (isGrouped) {
            const values = params
                .map((item, index) => {
                    const series = groupedSeries[item.seriesIndex ?? index];
                    const entry = series?.data.find((e) => categoryKey(e) === name);
                    const count = entry?.count ?? 0;
                    const seriesTotal =
                        series?.totalCount ??
                        series?.data.reduce((sum, e) => sum + e.count, 0) ??
                        0;
                    return `${item.marker ?? ''}${escape(item.seriesName ?? '')}: ${formatTooltipValue(count, seriesTotal)}`;
                })
                .join('<br/>');
            return `${header}<br/>${values}`;
        }

        const count = category?.count ?? 0;
        const filteredCount = category?.filteredCount;
        if (hasActiveFilter && filteredCount !== undefined && filteredCount !== count) {
            return `${header}<br/>Count: ${formatTooltipValue(filteredCount, totalCount)} of ${formatTooltipValue(count, totalCount)} total`;
        }
        return `${header}<br/>Count: ${formatTooltipValue(count, totalCount)}`;
    };
}
