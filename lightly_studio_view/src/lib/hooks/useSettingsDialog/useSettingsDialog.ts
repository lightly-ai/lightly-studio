import { readonly, writable } from 'svelte/store';

const DEFAULT_TAB = 'shortcuts';

const isSettingsDialogOpen = writable(false);
const initialTab = writable(DEFAULT_TAB);

export function useSettingsDialog() {
    /** Opens the dialog on the given tab, or on Shortcuts without one. */
    const openSettingsDialog = (tab: string = DEFAULT_TAB) => {
        initialTab.set(tab);
        isSettingsDialogOpen.set(true);
    };

    const closeSettingsDialog = () => {
        isSettingsDialogOpen.set(false);
    };

    return {
        isSettingsDialogOpen,
        initialTab: readonly(initialTab),
        openSettingsDialog,
        closeSettingsDialog
    };
}
