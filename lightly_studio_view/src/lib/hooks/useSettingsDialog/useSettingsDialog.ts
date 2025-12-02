import { writable } from 'svelte/store';

const isSettingsDialogOpen = writable(false);

export function useSettingsDialog() {
    const openSettingsDialog = () => {
        isSettingsDialogOpen.set(true);
    };

    const closeSettingsDialog = () => {
        isSettingsDialogOpen.set(false);
    };

    return {
        isSettingsDialogOpen,
        openSettingsDialog,
        closeSettingsDialog
    };
}
