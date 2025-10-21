import { get } from 'svelte/store';
import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';

const initializationState = new Map<string, boolean>();

export const useScrollRestoration = (key: string) => {
    const savedState = useSessionStorage<{
        position: number;
        filterHash: string;
    }>(key, { position: 0, filterHash: '' });

    const initialize = () => {
        if (!initializationState.get(key)) {
            savedState.set({ position: 0, filterHash: '' });
            initializationState.set(key, true);
        }
    };

    const savePosition = (position: number, filterHash: string) => {
        savedState.set({ position, filterHash });
    };

    const getRestoredPosition = (currentFilterHash: string): number => {
        const state = get(savedState);
        return state.filterHash === currentFilterHash ? state.position : 0;
    };

    return {
        initialize,
        savePosition,
        getRestoredPosition
    };
};
