import { writable, type Readable } from 'svelte/store';

// Create a single instance of the store that will be shared across components
interface UseCreateClassifiersReturn {
    isCreateClassifiersPanelOpen: Readable<boolean>;
    error: Readable<Error | null>;
    openCreateClassifiersPanel: () => void;
    closeCreateClassifiersPanel: () => void;
    toggleCreateClassifiersPanel: () => void;
}

const isCreateClassifiersPanelOpen = writable<boolean>(false);

export function useCreateClassifiersPanel(): UseCreateClassifiersReturn {
    const error = writable<Error | null>(null);

    return {
        error,
        isCreateClassifiersPanelOpen,
        openCreateClassifiersPanel: () => isCreateClassifiersPanelOpen.set(true),
        closeCreateClassifiersPanel: () => {
            isCreateClassifiersPanelOpen.set(false);
        },
        toggleCreateClassifiersPanel: () => isCreateClassifiersPanelOpen.update((value) => !value)
    };
}
