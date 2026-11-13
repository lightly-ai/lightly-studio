import type { SampleFilter } from '$lib/api/lightly_studio_local';
import { withoutUndefined } from './withoutUndefined';

type FilterOverrides<F> = {
    [K in Exclude<keyof F, 'filter_type' | 'sample_filter'>]?: F[K];
} & { sample_filter?: Partial<SampleFilter> };

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
    const result: Record<string, unknown> = withoutUndefined({ ...base, ...topOverrides });
    delete result.filter_type;
    if (sampleOverrides !== undefined) {
        result.sample_filter = withoutUndefined({ ...base?.sample_filter, ...sampleOverrides });
    }
    if (Object.keys((result.sample_filter as object | undefined) ?? {}).length === 0) {
        delete result.sample_filter;
    }
    if (Object.keys(result).length === 0) {
        return undefined;
    }
    return { ...result, filter_type: filterType } as F & { filter_type: T };
}
