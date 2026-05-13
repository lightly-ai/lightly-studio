import { writable } from 'svelte/store';

const selectedCollectionIds = writable<string[]>([]);
const collectionIdToName = writable<Record<string, string>>({});

export const useAnnotationCollectionsFilter = () => {
    return {
        selectedCollectionIds,
        setSelectedCollectionIds: (ids: string[]) => selectedCollectionIds.set(ids),
        collectionIdToName,
        setCollectionIdToName: (map: Record<string, string>) => collectionIdToName.set(map)
    };
};
