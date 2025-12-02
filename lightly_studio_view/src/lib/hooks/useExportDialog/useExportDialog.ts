import { writable } from 'svelte/store';

const isExportDialogOpen = writable(false);

export function useExportDialog() {
    const openExportDialog = () => {
        isExportDialogOpen.set(true);
    };

    const closeExportDialog = () => {
        isExportDialogOpen.set(false);
    };

    return {
        isExportDialogOpen,
        openExportDialog,
        closeExportDialog
    };
}
