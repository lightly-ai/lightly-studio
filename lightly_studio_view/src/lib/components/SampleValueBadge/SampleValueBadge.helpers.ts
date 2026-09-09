export function formatOrderValue(value: number): string {
    return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

export function hasValueBadge(
    orderValue?: number | null,
    similarityScore?: number | null
): boolean {
    return orderValue != null || similarityScore != null;
}
