import { writable } from 'svelte/store';

const datasetSplitCollectionId = writable<string | null>(null);

export function useDatasetSplitDialog() {
    return {
        datasetSplitCollectionId,
        openDatasetSplitDialog: (collectionId: string) =>
            datasetSplitCollectionId.set(collectionId),
        closeDatasetSplitDialog: () => datasetSplitCollectionId.set(null)
    };
}
