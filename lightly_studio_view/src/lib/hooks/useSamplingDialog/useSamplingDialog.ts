import { writable } from 'svelte/store';

const isSamplingDialogOpen = writable(false);

export function useSamplingDialog() {
    const openSamplingDialog = () => {
        isSamplingDialogOpen.set(true);
    };

    const closeSamplingDialog = () => {
        isSamplingDialogOpen.set(false);
    };

    return {
        isSamplingDialogOpen,
        openSamplingDialog,
        closeSamplingDialog
    };
}
