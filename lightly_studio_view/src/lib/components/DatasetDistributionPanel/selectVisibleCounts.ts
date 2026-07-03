import type { CategoryCount } from '$lib/components/BarChart';
import type { DistributionConfig } from './types';

/**
 * Applies the panel config: ranks classes by count (descending, ties broken
 * by name) or by name (ascending) and keeps the top `n`.
 */
export function selectVisibleCounts(
    data: CategoryCount[],
    config: Pick<DistributionConfig, 'n' | 'sortBy'>
): CategoryCount[] {
    const sorted = [...data].sort((a, b) =>
        config.sortBy === 'count'
            ? b.count - a.count || a.label.localeCompare(b.label)
            : a.label.localeCompare(b.label)
    );
    return sorted.slice(0, Math.max(config.n, 1));
}
