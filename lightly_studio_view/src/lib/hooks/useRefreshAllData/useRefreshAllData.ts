import { useQueryClient } from '@tanstack/svelte-query';
import { loadCollectionTags } from '$lib/hooks';

interface UseRefreshAllDataReturn {
    refreshAllData: (collectionId: string) => Promise<void>;
}

/** Refetches all data, e.g. after it changed outside the GUI. Tags have their own store. */
export function useRefreshAllData(): UseRefreshAllDataReturn {
    const client = useQueryClient();

    const refreshAllData = async (collectionId: string) => {
        await Promise.all([loadCollectionTags(collectionId), client.invalidateQueries()]);
    };

    return { refreshAllData };
}
