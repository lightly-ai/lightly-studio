import { derived, readonly, writable, type Readable, type Writable } from 'svelte/store';

export type PlotColorByType = 'annotation_label' | 'tags' | 'metadata';

interface UsePlotColorByTypeReturn {
    selectedColorByType: Readable<PlotColorByType | null>;
    setSelectedColorByType: (type: PlotColorByType | null) => void;
    clearSelectedColorByType: () => void;
    /** Metadata field the plot is colored by, for the `metadata` type. */
    selectedColorByKey: Writable<string | null>;
}

const selectedColorByTypeByCollection = writable<Record<string, PlotColorByType | null>>({});
// Kept per collection like the type, so a reopened plot is colored by the same metadata field.
const selectedColorByKeyByCollection = new Map<string, Writable<string | null>>();

const getSelectedColorByKey = (collectionId: string) => {
    let key = selectedColorByKeyByCollection.get(collectionId);
    if (!key) {
        key = writable<string | null>(null);
        selectedColorByKeyByCollection.set(collectionId, key);
    }
    return key;
};

export function usePlotColorByType(collectionId: string): UsePlotColorByTypeReturn {
    const selectedColorByType = derived(
        selectedColorByTypeByCollection,
        ($selectedColorByTypeByCollection) => $selectedColorByTypeByCollection[collectionId] ?? null
    );

    const setSelectedColorByType = (type: PlotColorByType | null) => {
        selectedColorByTypeByCollection.update((selectedByCollection) => ({
            ...selectedByCollection,
            [collectionId]: type
        }));
    };

    const clearSelectedColorByType = () => {
        setSelectedColorByType(null);
    };

    return {
        selectedColorByType: readonly(selectedColorByType),
        setSelectedColorByType,
        clearSelectedColorByType,
        selectedColorByKey: getSelectedColorByKey(collectionId)
    };
}
