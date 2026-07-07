/**
 * Filters class labels by a comma-separated query. Each term is matched
 * case-insensitively as a substring; terms are OR-combined
 * (e.g. "car, truck" matches both "car" and "truck").
 */
export function filterClasses(classes: string[], query: string): string[] {
    const terms = query
        .split(',')
        .map((term) => term.trim().toLowerCase())
        .filter((term) => term.length > 0);
    if (terms.length === 0) return classes;
    return classes.filter((label) => {
        const lower = label.toLowerCase();
        return terms.some((term) => lower.includes(term));
    });
}
