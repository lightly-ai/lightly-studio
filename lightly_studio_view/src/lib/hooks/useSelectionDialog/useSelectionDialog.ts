import { writable } from 'svelte/store';

const isSelectionDialogOpen = writable(false);

export function useSelectionDialog() {
    const openSelectionDialog = () => {
        isSelectionDialogOpen.set(true);
    };

    const closeSelectionDialog = () => {
        isSelectionDialogOpen.set(false);
    };

    return {
        isSelectionDialogOpen,
        openSelectionDialog,
        closeSelectionDialog
    };
}
