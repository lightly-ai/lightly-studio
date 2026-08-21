import type { CategoryCountSeries } from '$lib/components/BarChart/types';

/** Filters each series to only the visible labels while preserving the full-data total for percentage calculations. */
export function prepareVisibleSeries(
    series: CategoryCountSeries[],
    visibleLabels: Set<string>
): CategoryCountSeries[] {
    return series.map((item) => ({
        ...item,
        totalCount: item.totalCount ?? item.data.reduce((sum, c) => sum + c.count, 0),
        data: item.data.filter((count) => visibleLabels.has(count.label))
    }));
}
