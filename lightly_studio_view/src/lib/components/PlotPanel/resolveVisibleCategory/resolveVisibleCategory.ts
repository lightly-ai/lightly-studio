import { EXCLUDED_BY_FILTERS_CATEGORY, INCLUDED_BY_FILTERS_CATEGORY } from '../plotCategories';

/**
 * Resolves the pre-hiding bucket a point is displayed as:
 * - filtered out -> EXCLUDED_BY_FILTERS_CATEGORY
 * - otherwise the first non-hidden category
 * - otherwise (no categories, or all hidden) -> INCLUDED_BY_FILTERS_CATEGORY ("No category")
 *
 * `hiddenCategories` only skips hidden color slots here; routing a hidden bucket to
 * HIDDEN_CATEGORY happens in `usePlotData` after demotion, on the final category.
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
        return EXCLUDED_BY_FILTERS_CATEGORY;
    }

    for (const category of colorCategories) {
        if (!hiddenCategories.has(category)) {
            return category;
        }
    }

    return INCLUDED_BY_FILTERS_CATEGORY;
};
