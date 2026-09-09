import {
    buildCategoricalComparisonBuckets,
    buildCategoricalComparisonSeries,
    buildTagHistogramSeries,
    type DistributionSource
} from '$lib/components/DatasetDistributionPanel';
import type { CategoricalMetadataBucket } from '$lib/hooks/useCategoricalMetadataDistribution';
import type { SampleTagMetadataDistributions } from '$lib/hooks/useMetadataDistributionsBySampleTags';
import type { HistogramData, HistogramRange } from '$lib/components/Histogram';
import type { CategoricalMetadataValue } from '$lib/services/types';

/** The metadata-key descriptors the collection reports. */
interface MetadataInfo {
    name: string;
    type: string;
}

/** A sample tag as the comparison select offers it. */
interface ComparisonTagItem {
    value: string;
    label: string;
}

/**
 * Metadata keys whose values are categorical. Numeric keys come from the
 * histogram response instead, so they are not listed here.
 */
export const selectCategoricalMetadataKeys = (metadataInfo: MetadataInfo[] | undefined): string[] =>
    (metadataInfo ?? [])
        .filter((info) => info.type === 'string' || info.type === 'boolean')
        .map((info) => info.name);

/** The selected comparison tags, in the order the select offers them. */
export const selectComparisonSampleTags = (
    items: ComparisonTagItem[],
    selectedIds: string[]
): { id: string; label: string }[] =>
    items
        .filter(({ value }) => selectedIds.includes(value))
        .map(({ value, label }) => ({ id: value, label }));

interface MetadataDistributionSourceParams {
    /** Numeric distributions for the current view, keyed by metadata key. */
    histograms: Record<string, HistogramData>;
    /** Metadata keys that hold categorical values, in the order to show them. */
    categoricalKeys: string[];
    /** Categorical distributions for the current view, keyed by metadata key. */
    categorical: Record<string, CategoricalMetadataBucket[]>;
    /**
     * The same distributions with every sidebar filter applied, for the
     * background bars. Undefined while that second request is still in flight -
     * the panel then defers the background rather than drawing it at zero.
     */
    filteredCategorical?: Record<string, CategoricalMetadataBucket[]>;
    /** Active numeric filter per key; bins outside it render dimmed. */
    selectedRanges: Record<string, HistogramRange | undefined>;
    /** Active categorical filter per key. */
    selectedValues: Record<string, CategoricalMetadataValue[] | undefined>;
    /** Per-tag distributions backing the comparison series. */
    tagDistributions: SampleTagMetadataDistributions[];
    /** Whether the current view's categorical request is in flight. */
    categoricalLoading?: boolean;
    /** Message for a failed categorical request for the current view. */
    categoricalError?: string;
    /** Whether the per-tag comparison requests are in flight. */
    comparisonLoading?: boolean;
    /** Message for a failed per-tag comparison request. */
    comparisonError?: string;
}

/**
 * The distribution panel's "Metadata" source: one group per metadata key, each
 * rendering as a histogram (numeric) or a bar chart (categorical), with the
 * selected sample tags layered on as comparison series.
 *
 * Returns null when the dataset has no metadata at all, so the panel's source
 * picker does not offer a source that can never show anything.
 */
export function buildMetadataDistributionSource(
    params: MetadataDistributionSourceParams
): DistributionSource | null {
    const numericKeys = Object.keys(params.histograms);
    if (numericKeys.length === 0 && params.categoricalKeys.length === 0) return null;

    return {
        id: 'metadata',
        label: 'Metadata',
        groupLabel: 'Metadata key',
        valueNoun: 'samples',
        comparisonLoading: params.comparisonLoading,
        comparisonError: params.comparisonError,
        groups: [
            ...numericKeys.map((key) => buildNumericGroup(params, key)),
            ...params.categoricalKeys.map((key) => buildCategoricalGroup(params, key))
        ]
    };
}

const buildNumericGroup = (params: MetadataDistributionSourceParams, key: string) => ({
    id: key,
    label: key,
    histogram: params.histograms[key],
    histogramSeries: buildTagHistogramSeries(params.tagDistributions, key),
    // Highlight the active filter range; bins outside it dim.
    selectedRange: params.selectedRanges[key]
});

const buildCategoricalGroup = (params: MetadataDistributionSourceParams, key: string) => ({
    id: key,
    label: key,
    categorical: {
        buckets: params.categorical[key] ?? [],
        // undefined until the filtered query has returned so the distribution
        // panel waits before showing background bars.
        filteredBuckets: params.filteredCategorical?.[key],
        // Values only a comparison tag holds still need something to filter on.
        comparisonBuckets: buildCategoricalComparisonBuckets(params.tagDistributions, key),
        selectedValues: params.selectedValues[key] ?? [],
        loading: params.categoricalLoading,
        error: params.categoricalError
    },
    comparisonSeries: buildCategoricalComparisonSeries(params.tagDistributions, key)
});
