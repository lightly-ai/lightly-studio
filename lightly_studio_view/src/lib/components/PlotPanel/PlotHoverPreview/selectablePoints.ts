import { HIDDEN_CATEGORY, isUnselectableCategory } from '../plotCategories';

interface CreateSelectablePointCheckParams {
    category: Uint8Array | undefined;
    sampleIds: string[] | undefined;
    // Undefined when no filter is active.
    fulfilsFilter: ArrayLike<number> | undefined;
    pickedSampleIds: string[];
}

/**
 * Returns a check for the points that the user can hover and pick. A point greyed out by a plot
 * selection stays selectable if it passes the filters. A picked point always stays selectable,
 * so the user can remove it.
 */
export function createSelectablePointCheck(
    params: CreateSelectablePointCheckParams
): (index: number) => boolean {
    const { category, sampleIds, fulfilsFilter, pickedSampleIds } = params;
    const pickedSampleIdSet = new Set(pickedSampleIds);
    return (index) => {
        if (!category) return true;
        if (!fulfilsFilter) return !isUnselectableCategory(category[index]);
        const isPicked = sampleIds !== undefined && pickedSampleIdSet.has(sampleIds[index]);
        const passesFilter = fulfilsFilter[index] !== 0;
        return category[index] !== HIDDEN_CATEGORY && (passesFilter || isPicked);
    };
}
