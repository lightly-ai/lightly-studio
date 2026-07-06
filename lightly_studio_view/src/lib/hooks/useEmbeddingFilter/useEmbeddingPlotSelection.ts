import { derived, writable, type Readable } from 'svelte/store';

// Per-collection count of items currently selected by the embedding-plot lasso/rectangle.
//
// The selection itself is sent to the backend as geometry (see LIG-9903), so the frontend no
// longer keeps the selected sample-id list in the query filter. The plot still computes the
// in-polygon count client-side for highlighting, and propagates just that number here so the
// sidebar "Embedding Plot Filter" chip can show how many items are selected.
const selectionCountByCollection = writable<Record<string, number>>({});

export function setPlotSelectionCount(collectionId: string, count: number): void {
    selectionCountByCollection.update((counts) => ({ ...counts, [collectionId]: count }));
}

export function clearPlotSelectionCount(collectionId: string): void {
    selectionCountByCollection.update((counts) => {
        if (!(collectionId in counts)) {
            return counts;
        }
        const next = { ...counts };
        delete next[collectionId];
        return next;
    });
}

export function getPlotSelectionCount(collectionId: Readable<string>): Readable<number> {
    return derived(
        [selectionCountByCollection, collectionId],
        ([$counts, $collectionId]) => $counts[$collectionId] ?? 0
    );
}
