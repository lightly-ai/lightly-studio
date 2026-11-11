import type { FilterDimensions } from '$lib/api/lightly_studio_local';
import type { DimensionBounds } from '$lib/services/loadDimensionBounds';

/** Converts a nullable range into a filter range. `null` bounds become `undefined`. */
export function toRange(
    range: { min?: number | null; max?: number | null } | null | undefined
): FilterDimensions | undefined {
    if (!range) return undefined;
    return { min: range.min ?? undefined, max: range.max ?? undefined };
}

/**
 * Converts dimension bounds into width and height filter ranges. Both keys are always
 * present, so overrides can remove width and height from a filter.
 */
export function dimensionRanges(bounds: DimensionBounds | null | undefined): {
    width: FilterDimensions | undefined;
    height: FilterDimensions | undefined;
} {
    return {
        width: bounds ? toRange({ min: bounds.min_width, max: bounds.max_width }) : undefined,
        height: bounds ? toRange({ min: bounds.min_height, max: bounds.max_height }) : undefined
    };
}
