import { writable } from 'svelte/store';

const isOperatorsDialogOpen = writable(false);

export function useOperatorsDialog() {
    const openOperatorsDialog = () => {
        isOperatorsDialogOpen.set(true);
    };

    const closeOperatorsDialog = () => {
        isOperatorsDialogOpen.set(false);
    };

    return {
        isOperatorsDialogOpen,
        openOperatorsDialog,
        closeOperatorsDialog
    };
}
