import { useQueryClient } from '@tanstack/svelte-query';
import { useTags } from '$lib/hooks/useTags/useTags';

interface UseRefreshAllDataParams {
    collectionId: string;
}

interface UseRefreshAllDataReturn {
    refreshAllData: () => Promise<void>;
}

/** Refetches all data, e.g. after it changed outside the GUI. Tags have their own store. */
export function useRefreshAllData({
    collectionId
}: UseRefreshAllDataParams): UseRefreshAllDataReturn {
    const client = useQueryClient();
    const { loadTags } = useTags({ collection_id: collectionId });

    const refreshAllData = async () => {
        await Promise.all([loadTags(), client.invalidateQueries()]);
    };

    return { refreshAllData };
}
