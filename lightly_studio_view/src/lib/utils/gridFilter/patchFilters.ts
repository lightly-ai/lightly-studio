/**
 * Returns `params` with `patch` merged into its `filters`. Keeps `undefined` values as keys.
 * Never mutates `params`.
 */
export function patchFilters<P extends { filters?: object }>(
    params: P,
    patch: Partial<NonNullable<P['filters']>>
): P {
    return { ...params, filters: { ...params.filters, ...patch } };
}
