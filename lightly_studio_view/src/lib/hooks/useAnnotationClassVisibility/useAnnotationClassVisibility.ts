import { derived, type Readable } from 'svelte/store';
import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';

const STORAGE_KEY = 'lightlyStudio_hidden_annotation_classes';

const hiddenClassNamesStore = useSessionStorage<string[]>(STORAGE_KEY, []);

export function useAnnotationClassVisibility() {
    const isClassHidden = (labelName: string): Readable<boolean> =>
        derived(hiddenClassNamesStore, ($hidden) => $hidden.includes(labelName));

    const toggleClassVisibility = (labelName: string) => {
        hiddenClassNamesStore.update((hidden) => {
            if (hidden.includes(labelName)) {
                return hidden.filter((name) => name !== labelName);
            }
            return [...hidden, labelName];
        });
    };

    return {
        hiddenClassNamesStore,
        isClassHidden,
        toggleClassVisibility
    };
}
