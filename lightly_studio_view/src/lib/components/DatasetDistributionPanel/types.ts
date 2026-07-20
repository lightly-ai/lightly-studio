import type { CategoryCount, ChartNormalize, ChartScale } from '$lib/components/BarChart';
import type { ClassSetSelection } from '$lib/components/ClassSetConfig';
import type { MetadataDistributionFilter } from '$lib/hooks/useMetadataDistribution/useMetadataDistribution';

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
    /**
     * Pre-fetched counts for annotation-style groups. Omitted for metadata
     * groups, whose data is fetched per compared tag from the group `id` (the
     * metadata key).
     */
    data?: CategoryCount[];
}

/** A tag the user can overlay on a metadata distribution as one series. */
export interface DistributionCompareTag {
    /** Tag id. */
    id: string;
    /** Tag name shown in the chip and legend. */
    label: string;
    /** Grid filter scoping this tag's samples. */
    filter: MetadataDistributionFilter;
}

/**
 * A selectable distribution source. The same bar-chart UI can render class
 * labels, tags, any metadata key, or eval results — only the source of the
 * counts changes.
 */
export interface DistributionSource {
    id: string;
    label: string;
    /**
     * Source flavour. `'annotations'` (default) renders pre-fetched `data`;
     * `'metadata'` fetches per-tag series for the selected key group.
     */
    kind?: 'annotations' | 'metadata';
    /**
     * Which endpoint a metadata source fetches from (default `'metadata'`, keyed
     * by group). `'nn_distance'` fetches the computed nearest-neighbor
     * distance histogram instead, which needs no metadata key.
     */
    distributionEndpoint?: 'metadata' | 'nn_distance';
    /** Counts for a simple source. Mutually exclusive with `groups`. */
    data?: CategoryCount[];
    /** Sub-groups for a source that fans out into fields (e.g. metadata keys). */
    groups?: DistributionSourceGroup[];
    /** Noun for the header summary and value axis (default 'annotations'). */
    valueNoun?: string;
    /** Optional label for the sub-group picker (e.g. 'Metadata key'). */
    groupLabel?: string;

    // --- metadata sources only ---
    /** Collection to query for metadata distributions. */
    collectionId?: string;
    /** Implicit series for the active selection/filter (null = whole collection). */
    baseFilter?: MetadataDistributionFilter;
    /** Tags the user can overlay for comparison. */
    compareTags?: DistributionCompareTag[];
}

/** User-configurable view options for the distribution panel. */
export interface DistributionConfig extends ClassSetSelection<DistributionSortOption> {
    /** Bar orientation (default 'vertical'). */
    orientation: DistributionOrientation;
    /** Count vs within-series percentage (metadata sources; default 'percentage'). */
    normalize: ChartNormalize;
    /** Value-axis scale (default 'linear'). */
    scale: ChartScale;
}
