import type { CategoryCount } from '$lib/components/BarChart';
import type { ClassSetSelection } from '$lib/components/ClassSetConfig';
import { type AnnotationCountMode } from '$lib/api/lightly_studio_local/types.gen';
import type { HistogramData, HistogramRange } from '$lib/components/Histogram';

export type DistributionSortOption = 'count' | 'name';

export const DISTRIBUTION_SORT_LABELS: Record<DistributionSortOption, string> = {
    count: 'Count',
    name: 'Class name'
};

/** Bar layout for the distribution chart. */
export type DistributionOrientation = 'vertical' | 'horizontal';

/** Selectable bin counts for histogram sources (server default: 20). */
export const HISTOGRAM_BIN_COUNT_ITEMS = [10, 20, 50, 100];

/**
 * A selectable sub-group within a source. Used by sources that fan out into
 * several fields — e.g. one entry per metadata key.
 */
export interface DistributionSourceGroup {
    id: string;
    label: string;
    /** Category counts rendered as a bar chart. Mutually exclusive with `histogram`. */
    data?: CategoryCount[];
    /** Numeric bin distribution rendered as a histogram. Mutually exclusive with `data`. */
    histogram?: HistogramData;
    /**
     * Currently selected value range for a histogram group (e.g. the active
     * metadata filter). Bins outside it render dimmed.
     */
    selectedRange?: HistogramRange;
}

/**
 * A selectable distribution source. The same bar-chart UI can render class
 * labels, tags, any metadata key, or eval results — only the source of the
 * counts changes.
 */
export interface DistributionSource {
    id: string;
    label: string;
    /** Counts for a simple source. Mutually exclusive with `groups` and `histogram`. */
    data?: CategoryCount[];
    /** Numeric bin distribution rendered as a histogram. Mutually exclusive with `data`. */
    histogram?: HistogramData;
    /**
     * Currently selected value range for a source-level histogram (e.g. the active
     * filter). Bins outside it render dimmed.
     */
    selectedRange?: HistogramRange;
    /** Sub-groups for a source that fans out into fields (e.g. metadata keys). */
    groups?: DistributionSourceGroup[];
    /** Noun for the header summary and value axis (default 'annotations'). */
    valueNoun?: string;
    /** Optional label for the sub-group picker (e.g. 'Metadata key'). */
    groupLabel?: string;
}

/** User-configurable view options for the distribution panel. */
export interface DistributionConfig extends ClassSetSelection<DistributionSortOption> {
    /** Bar orientation (default 'vertical'). */
    orientation: DistributionOrientation;
    /** Whether to count annotation objects or distinct annotated samples (default OBJECTS). */
    countMode?: AnnotationCountMode;
}
