import { writable } from 'svelte/store';

const isTrainModelDialogOpen = writable(false);

export function useTrainModelDialog() {
    const openTrainModelDialog = () => isTrainModelDialogOpen.set(true);
    const closeTrainModelDialog = () => isTrainModelDialogOpen.set(false);

    return { isTrainModelDialogOpen, openTrainModelDialog, closeTrainModelDialog };
}
