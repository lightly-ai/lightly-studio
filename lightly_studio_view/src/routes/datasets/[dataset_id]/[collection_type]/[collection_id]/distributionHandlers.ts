import type { VideoFilter } from '$lib/api/lightly_studio_local';
import type { CategoryCount } from '$lib/components/BarChart';
import type {
    CategoricalMetadataValue,
    CategoricalMetadataValues,
    MetadataValues
} from '$lib/services/types';

type MetadataRange = MetadataValues[string];

/**
 * Maps annotation count rows to class bars. `current_count` is used so the plot
 * tracks the active filters, and classes with no matches in the current view
 * are dropped.
 */
export function toCategoryCounts(
    countsData: unknown[] | undefined,
    selectedLabels: string[]
): CategoryCount[] {
    return (countsData ?? [])
        .map((item) => {
            const row = item as { [key: string]: unknown };
            const label = String(row['label_name']);
            return {
                label,
                count: Number(row['current_count']),
                // Mirrors the sidebar's LabelsMenu selection so a class stays
                // highlighted in the plot after it's clicked into the filter.
                selected: selectedLabels.includes(label)
            };
        })
        .filter((item) => item.count > 0);
}

/**
 * Returns the next metadata range after a histogram selection (bin click or
 * press-drag-release). Selecting the current range again resets it to the
 * full bound.
 */
export function selectHistogramRange({
    bound,
    current,
    range
}: {
    bound: MetadataRange;
    current: MetadataRange | undefined;
    range: MetadataRange;
}): MetadataRange {
    // Clamp first, then compare: the stored value is always clamped to
    // bound, so checking raw range.min/max would miss re-clicks on bins
    // whose edges fall outside the collection's value range.
    const clampedMin = Math.max(range.min, bound.min);
    const clampedMax = Math.min(range.max, bound.max);
    const isBinAlreadySelected =
        current && current.min === clampedMin && current.max === clampedMax;
    return isBinAlreadySelected
        ? { min: bound.min, max: bound.max }
        : { min: clampedMin, max: clampedMax };
}

/** Adds the value to the selection, or removes it when it is already selected. */
export function toggleCategoricalValue(
    selected: CategoricalMetadataValue[],
    value: CategoricalMetadataValue
): CategoricalMetadataValue[] {
    const exists = selected.some((candidate) => Object.is(candidate, value));
    return exists
        ? selected.filter((candidate) => !Object.is(candidate, value))
        : [...selected, value];
}

/** Returns a copy of the categorical selection without the values of one key. */
export function withoutCategoricalValues(
    values: CategoricalMetadataValues,
    metadataKey: string
): CategoricalMetadataValues {
    const next = { ...values };
    delete next[metadataKey];
    return next;
}

/**
 * Keeps only the scope of the video grid filter: its tags and sample ids. The
 * distribution totals use this filter, so the bar heights stay stable while the
 * other sidebar filters change.
 */
export function selectVideoDistributionBaseFilter(
    filter: VideoFilter | null | undefined
): VideoFilter & { filter_type: 'video' } {
    const sampleIds = filter?.sample_filter?.sample_ids ?? [];
    const tagIds = filter?.sample_filter?.tag_ids ?? [];
    if (sampleIds.length === 0 && tagIds.length === 0) {
        return { filter_type: 'video' };
    }
    return {
        filter_type: 'video',
        sample_filter: {
            ...(sampleIds.length > 0 ? { sample_ids: sampleIds } : {}),
            ...(tagIds.length > 0 ? { tag_ids: tagIds } : {})
        }
    };
}
