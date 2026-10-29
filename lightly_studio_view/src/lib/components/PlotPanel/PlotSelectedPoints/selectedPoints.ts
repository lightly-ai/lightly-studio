import type { PlotSelectedPointSize } from '$lib/hooks/usePlotSelectedPointSize/usePlotSelectedPointSize';
import { INCLUDED_BY_FILTERS_CATEGORY } from '../plotCategories';

// Above this many selected points the overlay would slow down pan and zoom, so it is not drawn.
export const MAX_DRAWN_SELECTED_POINTS = 50_000;
// Radius in CSS pixels per setting. A regular point at the plot's automatic size is about 2.
const SELECTED_POINT_RADII: Record<PlotSelectedPointSize, number> = {
    small: 3,
    medium: 4,
    large: 5,
    extra_large: 7
};

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

/** Radius in CSS pixels of a selected point for the "Selected point size" setting. */
export function getSelectedPointRadius(size: PlotSelectedPointSize): number {
    return SELECTED_POINT_RADII[size];
}
