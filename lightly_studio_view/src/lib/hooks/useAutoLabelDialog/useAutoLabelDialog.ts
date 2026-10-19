import { writable } from 'svelte/store';

const isAutoLabelDialogOpen = writable(false);

export function useAutoLabelDialog() {
    return {
        isAutoLabelDialogOpen,
        openAutoLabelDialog: () => isAutoLabelDialogOpen.set(true),
        closeAutoLabelDialog: () => isAutoLabelDialogOpen.set(false)
    };
}
