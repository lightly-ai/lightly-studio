import { derived, writable, type Readable } from 'svelte/store';

// Per-collection count of items currently selected by the embedding-plot lasso/rectangle.
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
