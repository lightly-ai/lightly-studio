import {
    EXCLUDED_BY_FILTERS_CATEGORY,
    HIDDEN_CATEGORY,
    INCLUDED_BY_FILTERS_CATEGORY
} from '../plotCategories';

/**
 * Resolves the category a point is displayed as, given every category it belongs to in
 * priority order. Hidden categories are skipped so a multi-category point falls back to
 * its next visible category. When the reserved non-categorical row a point would resolve
 * to is itself hidden, the point is routed to HIDDEN_CATEGORY (transparent, not rendered,
 * not selectable):
 * - point does not fulfil the filter -> EXCLUDED_BY_FILTERS_CATEGORY,
 *   or HIDDEN_CATEGORY if that row is hidden
 * - otherwise the first category that is not hidden
 * - otherwise (no categories, or all hidden) -> INCLUDED_BY_FILTERS_CATEGORY (no category),
 *   or HIDDEN_CATEGORY if that row is hidden
 *
 * @param colorCategories - All categories the point belongs to, in priority order
 * @param fulfilsFilter - Whether the point passes the active filter (0 = filtered out)
 * @param hiddenCategories - Categories currently toggled off in the legend
 */
export const resolveVisibleCategory = (
    colorCategories: number[],
    fulfilsFilter: number,
    hiddenCategories: ReadonlySet<number>
): number => {
    if (fulfilsFilter === 0) {
        return hiddenCategories.has(EXCLUDED_BY_FILTERS_CATEGORY)
            ? HIDDEN_CATEGORY
            : EXCLUDED_BY_FILTERS_CATEGORY;
    }

    for (const category of colorCategories) {
        if (!hiddenCategories.has(category)) {
            return category;
        }
    }

    return hiddenCategories.has(INCLUDED_BY_FILTERS_CATEGORY)
        ? HIDDEN_CATEGORY
        : INCLUDED_BY_FILTERS_CATEGORY;
};
