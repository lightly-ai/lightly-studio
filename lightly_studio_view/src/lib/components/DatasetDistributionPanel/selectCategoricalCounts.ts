import type { CategoryCount, CategoryCountSeries } from '$lib/components/BarChart';
import { selectVisibleCounts } from './selectVisibleCounts';

const otherId = JSON.stringify(['other']);

/** Keep the selected values and combine the remaining values into Other. */
export function selectCategoricalCounts(
    data: CategoryCount[],
    config: Parameters<typeof selectVisibleCounts>[1]
): CategoryCount[] {
    const visible = selectVisibleCounts(data, config);
    return config.mode === 'topN' ? aggregateHiddenCounts(data, visible) : visible;
}

/** Use the same visible categories and Other bucket for every comparison tag. */
export function selectCategoricalSeries(
    series: CategoryCountSeries[],
    visible: CategoryCount[],
    aggregateOther: boolean
): CategoryCountSeries[] {
    const visibleKeys = new Set(visible.map((item) => item.id ?? item.label));
    return series.map((item) => ({
        ...item,
        totalCount: item.totalCount ?? item.data.reduce((sum, count) => sum + count.count, 0),
        data: aggregateOther
            ? aggregateHiddenCounts(
                  item.data,
                  item.data.filter((count) => visibleKeys.has(count.id ?? count.label))
              )
            : item.data.filter((count) => visibleKeys.has(count.id ?? count.label))
    }));
}

function aggregateHiddenCounts(data: CategoryCount[], visible: CategoryCount[]): CategoryCount[] {
    const visibleKeys = new Set(visible.map((item) => item.id ?? item.label));
    const hidden = data.filter((item) => !visibleKeys.has(item.id ?? item.label));
    if (hidden.length === 0) return visible;

    const existingOther = visible.find((item) => item.id === otherId);
    const aggregated = existingOther ? [...hidden, existingOther] : hidden;
    const hasLiteralOther = data.some((item) => item.label === 'Other' && item.id !== otherId);
    return [
        ...visible.filter((item) => item !== existingOther),
        {
            id: otherId,
            label: hasLiteralOther ? 'Other (aggregated)' : 'Other',
            count: aggregated.reduce((sum, item) => sum + item.count, 0),
            filteredCount: aggregated.some((item) => item.filteredCount !== undefined)
                ? aggregated.reduce((sum, item) => sum + (item.filteredCount ?? item.count), 0)
                : undefined,
            selectable: false,
            pinned: true
        }
    ];
}
