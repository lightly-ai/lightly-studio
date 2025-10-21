import { writable, type Readable } from 'svelte/store';
import type { RefineMode } from '$lib/services/types';

// Create a single instance of the store that will be shared across components
interface UseRefineClassifiersReturn {
    isRefineClassifiersPanelOpen: Readable<boolean>;
    currentMode: Readable<RefineMode | null>;
    currentClassifierName: Readable<string | null>;
    currentClassifierId: Readable<string | null>;
    currentClassifierClasses: Readable<string[] | null>;
    openRefineClassifiersPanel: (
        mode: RefineMode,
        classifierId: string,
        classifierName: string,
        classifierClasses: string[]
    ) => void;
    closeRefineClassifiersPanel: () => void;
    toggleRefineClassifiersPanel: () => void;
}
const isRefineClassifiersPanelOpen = writable<boolean>(false);
const currentMode = writable<RefineMode | null>(null);
const currentClassifierName = writable<string | null>(null);
const currentClassifierId = writable<string | null>(null);
const currentClassifierClasses = writable<string[] | null>(null);

export function useRefineClassifiersPanel(): UseRefineClassifiersReturn {
    const openRefineClassifiersPanel = (
        mode: RefineMode,
        classifierID: string,
        classifierName: string,
        classifierClasses: string[]
    ) => {
        currentMode.set(mode);
        isRefineClassifiersPanelOpen.set(true);
        currentClassifierId.set(classifierID);
        currentClassifierName.set(classifierName);
        currentClassifierClasses.set(classifierClasses);
    };
    return {
        isRefineClassifiersPanelOpen,
        currentMode,
        currentClassifierName,
        currentClassifierId,
        currentClassifierClasses,
        openRefineClassifiersPanel,
        closeRefineClassifiersPanel: () => {
            currentMode.set(null);
            isRefineClassifiersPanelOpen.set(false);
        },
        toggleRefineClassifiersPanel: () => {
            isRefineClassifiersPanelOpen.update((value: boolean) => !value);
        }
    };
}
