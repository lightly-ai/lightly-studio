export type DistributionSortOption = 'count' | 'name';

export const DISTRIBUTION_SORT_LABELS: Record<DistributionSortOption, string> = {
    count: 'Count',
    name: 'Class name'
};

/** Bar layout for the distribution chart. */
export type DistributionOrientation = 'vertical' | 'horizontal';

/** User-configurable view options for the distribution panel. */
export interface DistributionConfig {
    /** Number of top classes shown. */
    n: number;
    sortBy: DistributionSortOption;
    /** Bar orientation (default 'vertical'). */
    orientation: DistributionOrientation;
}
