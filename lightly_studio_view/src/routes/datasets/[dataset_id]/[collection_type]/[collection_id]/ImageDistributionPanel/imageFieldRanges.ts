import type { HistogramRange } from '$lib/components/Histogram';
import { toImageFieldId, type ImageField } from '$lib/hooks/useImageFieldDistribution';
import type { DimensionBounds } from '$lib/services/loadDimensionBounds';
import { selectHistogramRange } from '../distributionHandlers';

const BOUND_KEYS = {
    width: { min: 'min_width', max: 'max_width' },
    height: { min: 'min_height', max: 'max_height' }
} as const;

/** The width and height filter ranges, keyed by distribution group ID. */
export const selectImageFieldRanges = (
    values: DimensionBounds | null
): Record<string, HistogramRange> =>
    values
        ? Object.fromEntries(
              (Object.keys(BOUND_KEYS) as ImageField[]).map((field) => [
                  toImageFieldId(field),
                  { min: values[BOUND_KEYS[field].min], max: values[BOUND_KEYS[field].max] }
              ])
          )
        : {};

/**
 * The width and height filter after a range is selected on the histogram of `field`.
 * Selecting the current range again resets the filter to the full bounds.
 */
export const applyImageFieldRange = ({
    field,
    bounds,
    values,
    range
}: {
    field: ImageField;
    bounds: DimensionBounds;
    values: DimensionBounds;
    range: HistogramRange;
}): DimensionBounds => {
    const keys = BOUND_KEYS[field];
    // The filter holds whole pixels, while bin edges can fall between them.
    const min = Math.ceil(range.min);
    // Bins exclude their upper edge, except the last bin.
    const max = range.max >= bounds[keys.max] ? Math.floor(range.max) : Math.ceil(range.max) - 1;
    const selected = selectHistogramRange({
        bound: { min: bounds[keys.min], max: bounds[keys.max] },
        current: { min: values[keys.min], max: values[keys.max] },
        range: { min, max: Math.max(min, max) }
    });
    return { ...values, [keys.min]: selected.min, [keys.max]: selected.max };
};
