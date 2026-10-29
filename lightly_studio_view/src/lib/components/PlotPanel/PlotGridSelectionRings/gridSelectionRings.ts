import { HIDDEN_CATEGORY } from '../plotCategories';

// Above this many rings the overlay would slow down pan and zoom, so the rest are not drawn.
export const MAX_GRID_SELECTION_RINGS = 500;

/**
 * Returns the indices of the plot points of the samples selected in the grid, at most
 * `MAX_GRID_SELECTION_RINGS`. Samples without a point and hidden points are skipped.
 */
export function getGridSelectionPointIndices(
    selectedSampleIds: ReadonlySet<string>,
    sampleIndexById: ReadonlyMap<string, number>,
    category: ArrayLike<number> | undefined
): number[] {
    const indices: number[] = [];
    for (const sampleId of selectedSampleIds) {
        const index = sampleIndexById.get(sampleId);
        if (index === undefined || category?.[index] === HIDDEN_CATEGORY) continue;
        indices.push(index);
        if (indices.length === MAX_GRID_SELECTION_RINGS) break;
    }
    return indices;
}
