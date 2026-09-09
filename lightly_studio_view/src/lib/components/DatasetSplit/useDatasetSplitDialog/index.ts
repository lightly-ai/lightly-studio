import { writable } from 'svelte/store';

const isDatasetSplitDialogOpen = writable(false);

export function useDatasetSplitDialog() {
    return {
        isDatasetSplitDialogOpen,
        openDatasetSplitDialog: () => isDatasetSplitDialogOpen.set(true),
        closeDatasetSplitDialog: () => isDatasetSplitDialogOpen.set(false)
    };
}
