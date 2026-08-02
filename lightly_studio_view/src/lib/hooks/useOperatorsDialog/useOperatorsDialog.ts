import { writable } from 'svelte/store';
import type { OperatorProgress } from '$lib/api/lightly_studio_local';

const isOperatorsDialogOpen = writable(false);
const isPluginExecuting = writable(false);
const pluginProgress = writable<OperatorProgress | null>(null);

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

    // Null while the running plugin has not reported progress, which keeps the
    // overlay on its indeterminate spinner.
    const setPluginProgress = (progress: OperatorProgress | null) => {
        pluginProgress.set(progress);
    };

    return {
        isOperatorsDialogOpen,
        isPluginExecuting,
        pluginProgress,
        openOperatorsDialog,
        closeOperatorsDialog,
        setPluginExecuting,
        setPluginProgress
    };
}
