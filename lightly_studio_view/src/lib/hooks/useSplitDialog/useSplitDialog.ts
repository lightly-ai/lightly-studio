import { writable } from 'svelte/store';

// Module-level store so every invocation of useSplitDialog() (e.g. the trigger in
// the menu and the dialog component itself) shares the same open state.
const isSplitDialogOpen = writable(false);

export function useSplitDialog() {
    const openSplitDialog = () => isSplitDialogOpen.set(true);
    const closeSplitDialog = () => isSplitDialogOpen.set(false);

    return {
        isSplitDialogOpen,
        openSplitDialog,
        closeSplitDialog
    };
}
