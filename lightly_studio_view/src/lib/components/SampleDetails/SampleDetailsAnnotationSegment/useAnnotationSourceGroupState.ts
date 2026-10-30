import { useAnnotationCollectionsFilter } from '$lib/hooks';
import { writable } from 'svelte/store';

interface AnnotationSourceGroupState {
    open?: boolean;
    hidden?: boolean;
}

// Kept in memory only, so a page reload restores the defaults.
const sourceGroupStates = writable<Record<string, AnnotationSourceGroupState>>({});
let isWatchingGridFilter = false;

/**
 * Remembers the collapse and visibility the user set per annotation source, so they carry over
 * to the next sample.
 */
export function useAnnotationSourceGroupState() {
    if (!isWatchingGridFilter) {
        isWatchingGridFilter = true;
        watchGridFilter();
    }

    const setSourceGroupState = (sourceId: string, state: AnnotationSourceGroupState) => {
        sourceGroupStates.update((states) => ({
            ...states,
            [sourceId]: { ...states[sourceId], ...state }
        }));
    };

    return { sourceGroupStates, setSourceGroupState };
}

// A change of a source in the grid source filter replaces the visibility stored for it. The
// subscription stays open, because the filter changes in the grid while no sample is open.
function watchGridFilter() {
    let previousIds: string[] | undefined;
    useAnnotationCollectionsFilter().selectedCollectionIds.subscribe((selectedIds) => {
        const changedIds = new Set(
            [...selectedIds, ...(previousIds ?? selectedIds)].filter(
                (id) => selectedIds.includes(id) !== (previousIds ?? selectedIds).includes(id)
            )
        );
        previousIds = selectedIds;
        if (changedIds.size === 0) return;
        sourceGroupStates.update((states) =>
            Object.fromEntries(
                Object.entries(states).map(([id, state]) => [
                    id,
                    changedIds.has(id) ? { open: state.open } : state
                ])
            )
        );
    });
}
