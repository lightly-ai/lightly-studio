import { writable } from 'svelte/store';

const selectedCollectionIds = writable<string[]>([]);
const collectionIdToName = writable<Record<string, string>>({});
// Whether the selection has been explicitly set at least once this session.
// Distinguishes "never initialized" (e.g. deep link to a details page) from a
// selection the user deliberately cleared.
const isSelectionInitialized = writable<boolean>(false);

export const useAnnotationCollectionsFilter = () => {
    return {
        selectedCollectionIds,
        isSelectionInitialized,
        setSelectedCollectionIds: (ids: string[]) => {
            isSelectionInitialized.set(true);
            selectedCollectionIds.set(ids);
        },
        collectionIdToName,
        setCollectionIdToName: (map: Record<string, string>) => collectionIdToName.set(map)
    };
};
