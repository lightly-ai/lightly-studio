import { writable } from 'svelte/store';

interface AnnotationSourceGroupState {
    open?: boolean;
    hidden?: boolean;
}

// Kept in memory only, so a page reload restores the defaults.
const sourceGroupStates = writable<Record<string, AnnotationSourceGroupState>>({});

/**
 * Remembers the collapse and visibility the user set per annotation source, so they carry over
 * to the next sample.
 */
export function useAnnotationSourceGroupState() {
    const setSourceGroupState = (sourceId: string, state: AnnotationSourceGroupState) => {
        sourceGroupStates.update((states) => ({
            ...states,
            [sourceId]: { ...states[sourceId], ...state }
        }));
    };

    return { sourceGroupStates, setSourceGroupState };
}
