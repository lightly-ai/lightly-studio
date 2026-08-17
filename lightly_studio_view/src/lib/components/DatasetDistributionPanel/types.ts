import type { BarChartValueMode, CategoryCount } from '$lib/components/BarChart';
import type { ClassSetSelection } from '$lib/components/ClassSetConfig';
import type {
    AnnotationCountMode,
    SampleTagAnnotationCountsView
} from '$lib/api/lightly_studio_local/types.gen';
import type { HistogramData, HistogramRange } from '$lib/components/Histogram';
import type { CategoricalMetadataBucket } from '$lib/hooks/useCategoricalMetadataDistribution/types';
import type { CategoricalMetadataValue } from '$lib/services/types';

export type DistributionSortOption = 'count' | 'name';

export type CategoricalBucket =
    | {
          id: string;
          kind: 'value';
          label: string;
          count: number;
          value: CategoricalMetadataValue;
      }
    | {
          id: string;
          kind: 'missing';
          label: string;
          count: number;
          value: null;
      }
    | { id: string; kind: 'other'; label: string; count: number; value?: never };

export interface CategoricalDistribution {
    buckets: CategoricalBucket[];
    filteredBuckets?: Pick<CategoricalBucket, 'id' | 'count'>[];
    selectedValues: CategoricalMetadataValue[];
    loading?: boolean;
    error?: string;
}

export const DISTRIBUTION_SORT_LABELS: Record<DistributionSortOption, string> = {
    count: 'Count',
    name: 'Class name'
};

export const CATEGORICAL_DISTRIBUTION_SORT_LABELS: Record<DistributionSortOption, string> = {
    count: 'Count',
    name: 'Value'
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
    /** Counts grouped by the sample tags selected for comparison. */
    comparisonData?: SampleTagAnnotationCountsView[];
    /** Numeric bin distribution rendered as a histogram. Mutually exclusive with `data`. */
    histogram?: HistogramData;
    /**
     * Currently selected value range for a histogram group (e.g. the active
     * metadata filter). Bins outside it render dimmed.
     */
    selectedRange?: HistogramRange;
    /** Controlled categorical distribution and selection state. */
    categorical?: {
        buckets: CategoricalMetadataBucket[];
        /**
         * Buckets from the same query with all sidebar filters applied.
         * When provided, each bar shows a grey background at the full `count`
         * with a coloured foreground at the filtered count, giving context for
         * how active filters affect the distribution.
         * Omit (undefined) while the filtered query is still loading.
         */
        filteredBuckets?: CategoricalMetadataBucket[];
        selectedValues: CategoricalMetadataValue[];
        loading?: boolean;
        error?: string;
    };
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
    /** Counts grouped by the sample tags selected for comparison. */
    comparisonData?: SampleTagAnnotationCountsView[];
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
    /** Whether categorical distributions show counts or percentages. */
    valueMode?: BarChartValueMode;
}
