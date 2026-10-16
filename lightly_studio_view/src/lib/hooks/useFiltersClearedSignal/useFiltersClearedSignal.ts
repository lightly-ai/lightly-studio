import { readonly, writable, type Readable } from 'svelte/store';

const filtersClearedCount = writable(0);

interface UseFiltersClearedSignalReturn {
    filtersCleared: Readable<number>;
    signalFiltersCleared: () => void;
}

/**
 * Notifies components that keep their own filter state, for example remembered
 * metadata chips, that all filters were cleared at once.
 */
export function useFiltersClearedSignal(): UseFiltersClearedSignalReturn {
    return {
        filtersCleared: readonly(filtersClearedCount),
        signalFiltersCleared: () => filtersClearedCount.update((count) => count + 1)
    };
}
