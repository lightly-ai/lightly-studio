import type { CategoryCount } from '$lib/components/BarChart';

export type DistributionSortOption = 'count' | 'name';

export const DISTRIBUTION_SORT_LABELS: Record<DistributionSortOption, string> = {
    count: 'Count',
    name: 'Class name'
};

/** Bar layout for the distribution chart. */
export type DistributionOrientation = 'vertical' | 'horizontal';

/**
 * A selectable sub-group within a source. Used by sources that fan out into
 * several fields — e.g. one entry per metadata key.
 */
export interface DistributionSourceGroup {
    id: string;
    label: string;
    data: CategoryCount[];
}

/**
 * A selectable distribution source. The same bar-chart UI can render class
 * labels, tags, any metadata key, or eval results — only the source of the
 * counts changes.
 */
export interface DistributionSource {
    id: string;
    label: string;
    /** Counts for a simple source. Mutually exclusive with `groups`. */
    data?: CategoryCount[];
    /** Sub-groups for a source that fans out into fields (e.g. metadata keys). */
    groups?: DistributionSourceGroup[];
    /** Noun for the header summary and value axis (default 'annotations'). */
    valueNoun?: string;
    /** Optional label for the sub-group picker (e.g. 'Metadata key'). */
    groupLabel?: string;
}

/** User-configurable view options for the distribution panel. */
export interface DistributionConfig {
    /** Number of top classes shown. */
    n: number;
    sortBy: DistributionSortOption;
    /** Bar orientation (default 'vertical'). */
    orientation: DistributionOrientation;
}
