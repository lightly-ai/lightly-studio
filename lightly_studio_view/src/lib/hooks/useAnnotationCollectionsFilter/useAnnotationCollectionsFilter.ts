import { writable } from 'svelte/store';

const selectedCollectionIds = writable<string[]>([]);

export const useAnnotationCollectionsFilter = () => {
    return {
        selectedCollectionIds,
        setSelectedCollectionIds: (ids: string[]) => selectedCollectionIds.set(ids)
    };
};
