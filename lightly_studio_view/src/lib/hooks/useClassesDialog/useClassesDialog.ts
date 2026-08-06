import { writable } from 'svelte/store';

const isClassesDialogOpen = writable(false);

export function useClassesDialog() {
    const openClassesDialog = () => isClassesDialogOpen.set(true);
    const closeClassesDialog = () => isClassesDialogOpen.set(false);

    return { isClassesDialogOpen, openClassesDialog, closeClassesDialog };
}
