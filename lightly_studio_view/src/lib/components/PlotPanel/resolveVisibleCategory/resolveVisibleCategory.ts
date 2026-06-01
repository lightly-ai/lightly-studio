import { FILTERED_CATEGORY, NOT_FILTERED_CATEGORY } from '../plotCategories';

/**
 * Resolves the category a point is displayed as, given every category it belongs to in
 * priority order. Hidden categories are skipped so a multi-category point falls back to
 * its next visible category:
 * - point does not fulfil the filter -> NOT_FILTERED_CATEGORY
 * - otherwise the first category that is not hidden
 * - otherwise (no categories, or all hidden) -> FILTERED_CATEGORY (unassigned)
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
        return NOT_FILTERED_CATEGORY;
    }

    for (const category of colorCategories) {
        if (!hiddenCategories.has(category)) {
            return category;
        }
    }

    return FILTERED_CATEGORY;
};
