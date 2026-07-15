import { derived, get, type Readable } from 'svelte/store';
import { clearPlotSelectionCount, getPlotSelectionCount } from './useEmbeddingPlotSelection';

// Visibility/count behaviour for embedding-plot selections that are sent to the backend as
// geometry (images and annotations). Unlike the sample-id based `useFilterVisibility`, the
// frontend no longer holds the resolved ids, so the chip count comes from the plot-propagated
// count and the selection is toggled off by clearing the region entirely.
export function useRegionFilterVisibility(
    collectionId: Readable<string>,
    clearRegion: () => void,
    setRangeSelectionForCollection: (collectionId: string, selection: null) => void
) {
    const effectiveCount = getPlotSelectionCount(collectionId);
    const isVisible = derived(effectiveCount, ($count) => $count > 0);

    function clearFilter() {
        setRangeSelectionForCollection(get(collectionId), null);
        clearRegion();
        clearPlotSelectionCount(get(collectionId));
    }

    // The geometry selection has no separate "hidden" state to restore, so turning it off
    // simply clears it.
    function setVisibility(shouldShow: boolean) {
        if (!shouldShow) {
            clearFilter();
        }
    }

    return { effectiveCount, isVisible, setVisibility, clearFilter };
}
