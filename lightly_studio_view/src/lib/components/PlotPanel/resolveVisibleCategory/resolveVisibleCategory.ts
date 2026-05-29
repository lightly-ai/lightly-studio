import { FILTERED_CATEGORY, NOT_FILTERED_CATEGORY } from '../plotCategories';

/**
 * Resolves the category a point should be rendered as, given all categories it belongs to.
 *
 * Mirrors the backend's primary-category logic, with an extra hidden-aware step so a
 * multi-category sample falls back to its next visible category when one is toggled off:
 * - point does not fulfil the filter -> NOT_FILTERED_CATEGORY
 * - otherwise the first category (priority order) that is not hidden
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
