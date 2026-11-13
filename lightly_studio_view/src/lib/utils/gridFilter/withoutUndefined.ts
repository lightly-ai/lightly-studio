/** Copies `value` without the keys whose value is `undefined`. Keeps `null` and `[]`. */
export function withoutUndefined<T extends object>(value: T): Partial<T> {
    return Object.fromEntries(
        Object.entries(value).filter(([, entry]) => entry !== undefined)
    ) as Partial<T>;
}
