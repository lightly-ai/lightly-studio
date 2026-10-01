export const HIDDEN_CATEGORY = 0;
export const EXCLUDED_BY_FILTERS_CATEGORY = 1;
export const INCLUDED_BY_FILTERS_CATEGORY = 2;

// Labels for the reserved categories. The backend reserves indices 0, 1 and 2 by index only;
// the frontend owns their human-readable labels. Index 0 (Hidden) is transparent and has no
// legend row, so it carries no label.
export const EXCLUDED_BY_FILTERS_LABEL = 'Excluded by filters';
export const INCLUDED_BY_FILTERS_LABEL = 'Included by filters';
export const NO_CATEGORY_LABEL = 'No category';

export function isUnselectableCategory(category: number): boolean {
    return category === EXCLUDED_BY_FILTERS_CATEGORY || category === HIDDEN_CATEGORY;
}
