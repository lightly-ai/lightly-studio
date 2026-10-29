// Point sizes the control steps through. Null ("Auto") lets the plot pick the size.
export const POINT_SIZES: readonly (number | null)[] = [1, 2, null, 3, 4, 6];

/** Returns the point size one step smaller (`direction` -1) or larger (+1), clamped to the ends. */
export function getNextPointSize(current: number | null, direction: -1 | 1): number | null {
    const index = Math.max(0, POINT_SIZES.indexOf(current));
    const next = Math.min(POINT_SIZES.length - 1, Math.max(0, index + direction));
    return POINT_SIZES[next];
}
