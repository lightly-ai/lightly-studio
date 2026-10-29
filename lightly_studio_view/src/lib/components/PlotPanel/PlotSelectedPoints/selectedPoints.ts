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
 * Returns the indices of the points that the filters or the plot selection include, so they can
 * be drawn larger. Points left out are demoted to the Excluded category (or Hidden), so every
 * point at or above the Included category is included. Returns no indices while every point is
 * included, since enlarging all of them would only make the plot denser.
 */
export function getSelectedPointIndices(category: ArrayLike<number> | undefined): number[] {
    if (!category) {
        return [];
    }
    const indices: number[] = [];
    let someExcluded = false;
    for (let index = 0; index < category.length; index++) {
        if (category[index] >= INCLUDED_BY_FILTERS_CATEGORY) {
            indices.push(index);
            if (indices.length > MAX_DRAWN_SELECTED_POINTS) return [];
        } else {
            someExcluded = true;
        }
    }
    return someExcluded ? indices : [];
}

/** Radius in CSS pixels of a selected point for the "Selected point size" setting. */
export function getSelectedPointRadius(size: PlotSelectedPointSize): number {
    return SELECTED_POINT_RADII[size];
}
