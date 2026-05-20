import { derived, readonly, writable, type Readable } from 'svelte/store';

type PlotColorByType = 'annotation_label' | 'tags' | 'metadata';

interface UsePlotColorByTypeReturn {
    selectedColorByType: Readable<PlotColorByType | null>;
    setSelectedColorByType: (type: PlotColorByType | null) => void;
    clearSelectedColorByType: () => void;
}

const selectedColorByTypeByCollection = writable<Record<string, PlotColorByType | null>>({});

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
        clearSelectedColorByType
    };
}
