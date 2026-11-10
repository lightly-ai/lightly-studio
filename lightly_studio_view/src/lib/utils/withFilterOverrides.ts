import type { DimensionBounds } from '$lib/services/loadDimensionBounds';
import type { FilterDimensions, SampleFilter } from '$lib/api/lightly_studio_local';

type FilterOverrides<F> = {
    [K in Exclude<keyof F, 'filter_type' | 'sample_filter'>]?: F[K];
} & { sample_filter?: Partial<SampleFilter> };

/**
 * Copies `source` and applies `overrides`. A key present in `overrides` replaces the
 * source value, and `undefined` removes the key. Absent keys pass through.
 */
function applyOverrides(source: object, overrides: object): Record<string, unknown> {
    const result: Record<string, unknown> = { ...source };
    for (const [key, value] of Object.entries(overrides)) {
        if (value === undefined) {
            delete result[key];
        } else {
            result[key] = value;
        }
    }
    return result;
}

/**
 * Builds a filter of the given type from `base` with `overrides` applied.
 * Returns `undefined` when nothing but `filter_type` is left. Never mutates `base`.
 */
export function withFilterOverrides<
    F extends { filter_type?: string; sample_filter?: SampleFilter | null },
    T extends NonNullable<F['filter_type']>
>(
    filterType: T,
    base: F | null | undefined,
    overrides: FilterOverrides<F>
): (F & { filter_type: T }) | undefined {
    const { sample_filter: sampleOverrides, ...topOverrides } = overrides;
    const result = applyOverrides(base ?? {}, topOverrides);
    // Object.entries skips absent keys; a present key with undefined value is removed above.
    if (Object.hasOwn(overrides, 'sample_filter') && sampleOverrides === undefined) {
        delete result.sample_filter;
    } else if (sampleOverrides !== undefined) {
        result.sample_filter = applyOverrides(base?.sample_filter ?? {}, sampleOverrides);
    }
    delete result.filter_type;

    const sampleFilter = result.sample_filter as object | undefined;
    if (sampleFilter && Object.keys(sampleFilter).length === 0) {
        delete result.sample_filter;
    }
    if (Object.keys(result).length === 0) {
        return undefined;
    }
    return { ...result, filter_type: filterType } as F & { filter_type: T };
}

interface ImageDimensionRanges {
    width: FilterDimensions | undefined;
    height: FilterDimensions | undefined;
}

/** Converts image dimension bounds into width and height filter ranges. */
export function imageDimensionRanges(
    bounds: DimensionBounds | null | undefined
): ImageDimensionRanges {
    return {
        width:
            bounds && (bounds.min_width !== undefined || bounds.max_width !== undefined)
                ? { min: bounds.min_width, max: bounds.max_width }
                : undefined,
        height:
            bounds && (bounds.min_height !== undefined || bounds.max_height !== undefined)
                ? { min: bounds.min_height, max: bounds.max_height }
                : undefined
    };
}
