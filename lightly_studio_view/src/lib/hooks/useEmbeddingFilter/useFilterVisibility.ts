import { derived, get, type Readable } from 'svelte/store';
import { useHiddenFilters } from './useHiddenFilters';

export function useFilterVisibility(
    collectionId: Readable<string>,
    activeSampleIds: Readable<string[]>,
    updateSampleIds: (ids: string[]) => void,
    setRangeSelectionForCollection: (collectionId: string, selection: null) => void
) {
    const { hiddenSampleIds, setHidden, clearHidden } = useHiddenFilters(collectionId);

    const effectiveCount = derived([activeSampleIds, hiddenSampleIds], ([$active, $hidden]) =>
        $active.length > 0 ? $active.length : $hidden.length
    );

    const isVisible = derived(activeSampleIds, ($active) => $active.length > 0);

    function setVisibility(shouldShow: boolean) {
        if (!shouldShow) {
            const activeIds = get(activeSampleIds);
            if (activeIds.length === 0) return;
            setHidden(activeIds);
            updateSampleIds([]);
            return;
        }
        const hiddenIds = get(hiddenSampleIds);
        if (get(activeSampleIds).length === 0 && hiddenIds.length > 0) {
            updateSampleIds(hiddenIds);
            if (get(activeSampleIds).length > 0) {
                clearHidden();
            }
        }
    }

    function clearFilter() {
        setRangeSelectionForCollection(get(collectionId), null);
        clearHidden();
        updateSampleIds([]);
    }

    return { effectiveCount, isVisible, setVisibility, clearFilter };
}
