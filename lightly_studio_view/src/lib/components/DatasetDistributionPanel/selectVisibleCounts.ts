import type { CategoryCount } from '$lib/components/BarChart';
import type { DistributionConfig } from './types';

/**
 * Applies the panel config: ranks classes by count (descending, ties broken
 * by name) or by name (ascending), then keeps either the top `n` (top-N mode)
 * or the explicitly selected labels (manual mode).
 */
export function selectVisibleCounts(
    data: CategoryCount[],
    config: Pick<DistributionConfig, 'mode' | 'n' | 'sortBy' | 'manualClasses'>
): CategoryCount[] {
    const sorted = [...data].sort((a, b) =>
        config.sortBy === 'count'
            ? b.count - a.count || a.label.localeCompare(b.label)
            : a.label.localeCompare(b.label)
    );
    if (config.mode === 'manual') {
        return sorted.filter((item) => config.manualClasses.includes(item.id ?? item.label));
    }
    const limit = Math.max(config.n, 1);
    const pinned = sorted.filter((item) => item.pinned);
    if (pinned.length === 0) return sorted.slice(0, limit);

    const remainingSlots = Math.max(limit - pinned.length, 0);
    const selected = new Set([
        ...pinned,
        ...sorted.filter((item) => !item.pinned).slice(0, remainingSlots)
    ]);
    return sorted.filter((item) => selected.has(item));
}
