import { INCLUDED_BY_FILTERS_CATEGORY } from '../plotCategories';

// Above this many selected points the overlay would slow down pan and zoom, so it is not drawn.
export const MAX_DRAWN_SELECTED_POINTS = 50_000;
// The plot library picks its own point size when none is set; this approximates it.
const AUTO_POINT_SIZE = 4;

/**
 * Returns the indices of the points inside the current plot selection. Points outside the
 * selection are demoted to the Excluded category (or Hidden), so every point at or above the
 * Included category is selected. Returns no indices while there is no selection.
 */
export function getSelectedPointIndices(
    category: ArrayLike<number> | undefined,
    hasSelection: boolean
): number[] {
    if (!category || !hasSelection) {
        return [];
    }
    const indices: number[] = [];
    for (let index = 0; index < category.length; index++) {
        if (category[index] >= INCLUDED_BY_FILTERS_CATEGORY) {
            indices.push(index);
            if (indices.length > MAX_DRAWN_SELECTED_POINTS) return [];
        }
    }
    return indices;
}

/** Radius in CSS pixels of a selected point, larger than a regular point of `pointSize`. */
export function getSelectedPointRadius(pointSize: number | null): number {
    return (pointSize ?? AUTO_POINT_SIZE) / 2 + 1.5;
}
