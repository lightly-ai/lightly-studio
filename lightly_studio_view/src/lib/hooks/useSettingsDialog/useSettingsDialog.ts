import { writable } from 'svelte/store';

const isSettingsDialogOpen = writable(false);
const settingsDialogTab = writable<string | undefined>(undefined);

export function useSettingsDialog() {
    // Opens the dialog on the given tab, or on the default tab.
    const openSettingsDialog = (tab?: string) => {
        settingsDialogTab.set(tab);
        isSettingsDialogOpen.set(true);
    };

    const closeSettingsDialog = () => {
        isSettingsDialogOpen.set(false);
    };

    return {
        isSettingsDialogOpen,
        settingsDialogTab,
        openSettingsDialog,
        closeSettingsDialog
    };
}
