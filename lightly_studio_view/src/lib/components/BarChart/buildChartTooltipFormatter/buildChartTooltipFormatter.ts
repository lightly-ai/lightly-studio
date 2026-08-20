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

/** Builds the ECharts tooltip formatter for grouped or standard bar charts. */
export function buildChartTooltipFormatter(
    isGrouped: boolean,
    data: CategoryCount[],
    groupedSeries: CategoryCountSeries[],
    totalCount: number,
    hasActiveFilter: boolean
): (params: TooltipParam[]) => string {
    return (params: TooltipParam[]) => {
        if (params.length === 0) return '';
        const [{ name }] = params;

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
            return `<b>${escape(name)}</b><br/>${values}`;
        }

        const entry = data.find((e) => categoryKey(e) === name);
        const count = entry?.count ?? 0;
        const filteredCount = entry?.filteredCount;
        const header = `<b>${escape(entry?.label ?? name)}</b>`;
        if (hasActiveFilter && filteredCount !== undefined && filteredCount !== count) {
            return `${header}<br/>Count: ${formatTooltipValue(filteredCount, totalCount)} of ${formatTooltipValue(count, totalCount)} total`;
        }
        return `${header}<br/>Count: ${formatTooltipValue(count, totalCount)}`;
    };
}
