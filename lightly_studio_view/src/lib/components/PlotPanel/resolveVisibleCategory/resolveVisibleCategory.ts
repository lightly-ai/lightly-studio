import {
    EXCLUDED_BY_FILTERS_CATEGORY,
    HIDDEN_CATEGORY,
    INCLUDED_BY_FILTERS_CATEGORY
} from '../plotCategories';

/**
 * Resolves the category a point is displayed as, given every category it belongs to in
 * priority order. A multi-category point falls back to its next visible category, and a
 * point whose resolved category is hidden routes to HIDDEN_CATEGORY (not rendered):
 * - filtered out -> EXCLUDED_BY_FILTERS_CATEGORY
 * - otherwise the first non-hidden category
 * - otherwise (no categories, or all hidden) -> INCLUDED_BY_FILTERS_CATEGORY
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
