import { derived, writable } from 'svelte/store';

const focusedPlotSampleIdByCollection = writable<Record<string, string | null>>({});

/**
 * Tracks the sample id of the most recently clicked embedding-plot point,
 * keyed by collection so switching tabs does not leak focus.
 */
export const usePlotPointFocus = (collectionId: string) => {
    const focusedPlotSampleId = derived(
        focusedPlotSampleIdByCollection,
        ($ids) => $ids[collectionId] ?? null
    );

    return {
        focusedPlotSampleId,
        setFocusedPlotSampleId: (sampleId: string | null) => {
            focusedPlotSampleIdByCollection.update((state) => ({
                ...state,
                [collectionId]: sampleId
            }));
        }
    };
};
