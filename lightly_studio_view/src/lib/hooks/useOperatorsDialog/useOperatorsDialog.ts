import { writable } from 'svelte/store';

const isOperatorsDialogOpen = writable(false);
const isPluginExecuting = writable(false);

export function useOperatorsDialog() {
    const openOperatorsDialog = () => {
        isOperatorsDialogOpen.set(true);
    };

    const closeOperatorsDialog = () => {
        isOperatorsDialogOpen.set(false);
    };

    const setPluginExecuting = (executing: boolean) => {
        isPluginExecuting.set(executing);
    };

    return {
        isOperatorsDialogOpen,
        isPluginExecuting,
        openOperatorsDialog,
        closeOperatorsDialog,
        setPluginExecuting
    };
}
