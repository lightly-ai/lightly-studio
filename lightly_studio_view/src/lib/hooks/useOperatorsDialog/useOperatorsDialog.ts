import { writable } from 'svelte/store';

const isOperatorsDialogOpen = writable(false);
const operatorDatasetId = writable<string | undefined>(undefined);

export function useOperatorsDialog() {
    const openOperatorsDialog = (datasetId?: string) => {
        operatorDatasetId.set(datasetId);
        isOperatorsDialogOpen.set(true);
    };

    const closeOperatorsDialog = () => {
        isOperatorsDialogOpen.set(false);
        operatorDatasetId.set(undefined);
    };

    return {
        isOperatorsDialogOpen,
        operatorDatasetId,
        openOperatorsDialog,
        closeOperatorsDialog
    };
}
